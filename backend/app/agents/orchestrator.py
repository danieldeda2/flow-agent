from langchain_anthropic import ChatAnthropic
from langchain.tools import tool
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, Optional, Callable
import operator
import requests
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from slack_sdk import WebClient
import base64
import os
import time
import email.mime.text
import email.mime.multipart
from datetime import datetime, timedelta

llm = ChatAnthropic(model="claude-sonnet-4-6")

class OrchestratorState(TypedDict):
    messages: Annotated[list, operator.add]
    github_token: Optional[str]
    gmail_token: Optional[str]
    gmail_refresh_token: Optional[str]
    gmail_expires_at: Optional[datetime]
    slack_token: Optional[str]
    output: str

def get_gmail_service(
    access_token: str,
    refresh_token: str,
    expires_at: Optional[datetime] = None,
    readonly: bool = True,
    on_refresh: Optional[Callable[[str, datetime], None]] = None
):
    print(f"get_gmail_service called, expires_at: {expires_at}")
    print(f"token_expired check: {expires_at and datetime.utcnow() >= expires_at}")
    scope = "https://www.googleapis.com/auth/gmail.readonly" if readonly else "https://mail.google.com/"
    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        scopes=[scope]
    )
    token_expired = expires_at and datetime.utcnow() >= expires_at
    if token_expired and creds.refresh_token:
        creds.refresh(Request())
        print(f"Token refreshed successfully, new token: {creds.token[:20]}...")
        if on_refresh:
            new_expires_at = datetime.utcnow() + timedelta(hours=1)
            on_refresh(creds.token, new_expires_at)
            print("DB updated with new token")
    return build("gmail", "v1", credentials=creds)

def get_github_username(token: str) -> str:
    response = requests.get(
        "https://api.github.com/user",
        headers={"Authorization": f"Bearer {token}"}
    )
    return response.json().get("login", "")

def make_orchestrator_tools(github_token, gmail_token, gmail_refresh_token, slack_token, gmail_expires_at=None, on_gmail_refresh=None):

    # ─── GITHUB TOOLS ────────────────────────────────────────────────

    @tool
    def get_github_repos() -> str:
        """Get all GitHub repositories for the user."""
        if not github_token:
            return "GitHub is not connected."
        username = get_github_username(github_token)
        response = requests.get(
            "https://api.github.com/user/repos",
            headers={"Authorization": f"Bearer {github_token}"}
        )
        repos = [r["name"] for r in response.json()]
        return f"GitHub username: {username}\nRepositories: {', '.join(repos)}"

    @tool
    def get_github_issues(repo_name: str) -> str:
        """Get open issues for a GitHub repository. repo_name should be just the repo name."""
        if not github_token:
            return "GitHub is not connected."
        username = get_github_username(github_token)
        if not username:
            return "Could not determine GitHub username"
        response = requests.get(
            f"https://api.github.com/repos/{username}/{repo_name}/issues",
            headers={"Authorization": f"Bearer {github_token}"}
        )
        if response.status_code != 200:
            return f"Could not fetch issues: {response.status_code}"
        issues = response.json()
        if not isinstance(issues, list):
            return f"Unexpected response: {issues}"
        formatted = ", ".join([f"#{i['number']}: {i['title']}" for i in issues])
        return f"Issues in {repo_name}: {formatted}" if issues else f"No open issues in {repo_name}"

    @tool
    def create_github_issue(repo_name: str, title: str, body: str) -> str:
        """Create a new issue in a GitHub repository."""
        if not github_token:
            return "GitHub is not connected."
        username = get_github_username(github_token)
        if not username:
            return "Could not determine GitHub username"
        response = requests.post(
            f"https://api.github.com/repos/{username}/{repo_name}/issues",
            headers={"Authorization": f"Bearer {github_token}"},
            json={"title": title, "body": body}
        )
        if response.status_code == 201:
            return f"Issue created: {response.json()['html_url']}"
        return f"Failed to create issue: {response.status_code} {response.text}"

    @tool
    def close_github_issue(repo_name: str, issue_number: int) -> str:
        """Close an existing GitHub issue by issue number."""
        if not github_token:
            return "GitHub is not connected."
        username = get_github_username(github_token)
        if not username:
            return "Could not determine GitHub username"
        response = requests.patch(
            f"https://api.github.com/repos/{username}/{repo_name}/issues/{issue_number}",
            headers={"Authorization": f"Bearer {github_token}"},
            json={"state": "closed"}
        )
        if response.status_code == 200:
            return f"Issue #{issue_number} closed successfully."
        return f"Failed to close issue: {response.status_code} {response.text}"

    @tool
    def comment_on_github_issue(repo_name: str, issue_number: int, comment: str) -> str:
        """Add a comment to an existing GitHub issue."""
        if not github_token:
            return "GitHub is not connected."
        username = get_github_username(github_token)
        if not username:
            return "Could not determine GitHub username"
        response = requests.post(
            f"https://api.github.com/repos/{username}/{repo_name}/issues/{issue_number}/comments",
            headers={"Authorization": f"Bearer {github_token}"},
            json={"body": comment}
        )
        if response.status_code == 201:
            return f"Comment added: {response.json()['html_url']}"
        return f"Failed to add comment: {response.status_code} {response.text}"

    @tool
    def get_github_pull_requests(repo_name: str) -> str:
        """Get open pull requests for a GitHub repository."""
        if not github_token:
            return "GitHub is not connected."
        username = get_github_username(github_token)
        if not username:
            return "Could not determine GitHub username"
        response = requests.get(
            f"https://api.github.com/repos/{username}/{repo_name}/pulls",
            headers={"Authorization": f"Bearer {github_token}"}
        )
        if response.status_code != 200:
            return f"Could not fetch pull requests: {response.status_code}"
        prs = response.json()
        if not prs:
            return f"No open pull requests in {repo_name}"
        formatted = ", ".join([f"#{pr['number']}: {pr['title']} (by {pr['user']['login']})" for pr in prs])
        return f"Open PRs in {repo_name}: {formatted}"

    @tool
    def get_github_commits(repo_name: str) -> str:
        """Get recent commit history for a GitHub repository."""
        if not github_token:
            return "GitHub is not connected."
        username = get_github_username(github_token)
        if not username:
            return "Could not determine GitHub username"
        response = requests.get(
            f"https://api.github.com/repos/{username}/{repo_name}/commits",
            headers={"Authorization": f"Bearer {github_token}"},
            params={"per_page": 10}
        )
        if response.status_code != 200:
            return f"Could not fetch commits: {response.status_code}"
        commits = response.json()
        if not commits:
            return f"No commits found in {repo_name}"
        formatted = "\n".join([
            f"- {c['sha'][:7]}: {c['commit']['message'].splitlines()[0]} ({c['commit']['author']['name']})"
            for c in commits
        ])
        return f"Recent commits in {repo_name}:\n{formatted}"

    # ─── GMAIL TOOLS ─────────────────────────────────────────────────

    @tool
    def get_unread_emails() -> str:
        """Get unread emails from Gmail. Returns message IDs and metadata."""
        if not gmail_token:
            return "Gmail is not connected."
        service = get_gmail_service(gmail_token, gmail_refresh_token, expires_at=gmail_expires_at, on_refresh=on_gmail_refresh)
        results = service.users().messages().list(
            userId="me", q="is:unread", maxResults=10
        ).execute()
        messages = results.get("messages", [])
        if not messages:
            return "No unread emails"
        emails = []
        for msg in messages:
            detail = service.users().messages().get(
                userId="me", id=msg["id"], format="metadata",
                metadataHeaders=["From", "Subject"]
            ).execute()
            headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
            emails.append(f"MESSAGE_ID={msg['id']} | From: {headers.get('From')} | Subject: {headers.get('Subject')}")
        return "\n".join(emails)

    @tool
    def get_email_body(message_id: str) -> str:
        """Get the full body of a specific email by MESSAGE_ID."""
        if not gmail_token:
            return "Gmail is not connected."
        service = get_gmail_service(gmail_token, gmail_refresh_token, expires_at=gmail_expires_at, on_refresh=on_gmail_refresh)
        detail = service.users().messages().get(
            userId="me", id=message_id, format="full"
        ).execute()
        payload = detail.get("payload", {})
        body = ""
        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain":
                    data = part["body"].get("data", "")
                    body = base64.urlsafe_b64decode(data).decode("utf-8")
                    break
        elif "body" in payload:
            data = payload["body"].get("data", "")
            if data:
                body = base64.urlsafe_b64decode(data).decode("utf-8")
        return body[:2000] if body else "Could not extract body"

    @tool
    def search_emails(query: str) -> str:
        """Search emails by keyword, sender, subject, or any Gmail search query."""
        if not gmail_token:
            return "Gmail is not connected."
        service = get_gmail_service(gmail_token, gmail_refresh_token, expires_at=gmail_expires_at, on_refresh=on_gmail_refresh)
        results = service.users().messages().list(
            userId="me", q=query, maxResults=10
        ).execute()
        messages = results.get("messages", [])
        if not messages:
            return f"No emails found for query: {query}"
        emails = []
        for msg in messages:
            detail = service.users().messages().get(
                userId="me", id=msg["id"], format="metadata",
                metadataHeaders=["From", "Subject", "Date"]
            ).execute()
            headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
            emails.append(f"MESSAGE_ID={msg['id']} | From: {headers.get('From')} | Subject: {headers.get('Subject')} | Date: {headers.get('Date')}")
        return "\n".join(emails)

    @tool
    def mark_email_as_read(message_id: str) -> str:
        """Mark a specific email as read by MESSAGE_ID."""
        if not gmail_token:
            return "Gmail is not connected."
        service = get_gmail_service(gmail_token, gmail_refresh_token, expires_at=gmail_expires_at, on_refresh=on_gmail_refresh)
        service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"removeLabelIds": ["UNREAD"]}
        ).execute()
        return f"Email {message_id} marked as read."

    @tool
    def send_email(to: str, subject: str, body: str) -> str:
        """Send an email via Gmail. to is the recipient email address."""
        if not gmail_token:
            return "Gmail is not connected."
        service = get_gmail_service(gmail_token, gmail_refresh_token, expires_at=gmail_expires_at, readonly=False, on_refresh=on_gmail_refresh)
        message = email.mime.multipart.MIMEMultipart()
        message["to"] = to
        message["subject"] = subject
        message.attach(email.mime.text.MIMEText(body, "plain"))
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        result = service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()
        return f"Email sent successfully. Message ID: {result['id']}"

    @tool
    def reply_to_email(message_id: str, body: str) -> str:
        """Reply to an existing email by MESSAGE_ID."""
        if not gmail_token:
            return "Gmail is not connected."
        service = get_gmail_service(gmail_token, gmail_refresh_token, expires_at=gmail_expires_at, readonly=False, on_refresh=on_gmail_refresh)
        original = service.users().messages().get(
            userId="me", id=message_id, format="metadata",
            metadataHeaders=["From", "Subject", "Message-ID"]
        ).execute()
        headers = {h["name"]: h["value"] for h in original["payload"]["headers"]}
        reply = email.mime.multipart.MIMEMultipart()
        reply["to"] = headers.get("From", "")
        reply["subject"] = f"Re: {headers.get('Subject', '')}"
        reply["In-Reply-To"] = headers.get("Message-ID", "")
        reply["References"] = headers.get("Message-ID", "")
        reply.attach(email.mime.text.MIMEText(body, "plain"))
        raw = base64.urlsafe_b64encode(reply.as_bytes()).decode("utf-8")
        result = service.users().messages().send(
            userId="me",
            body={"raw": raw, "threadId": original["threadId"]}
        ).execute()
        return f"Reply sent successfully. Message ID: {result['id']}"

    # ─── SLACK TOOLS ─────────────────────────────────────────────────

    @tool
    def get_slack_channels() -> str:
        """Get all Slack channels."""
        if not slack_token:
            return "Slack is not connected."
        client = WebClient(token=slack_token)
        result = client.conversations_list(types="public_channel,private_channel")
        channels = [f"#{c['name']} (id: {c['id']})" for c in result["channels"]]
        return f"Channels: {', '.join(channels)}"

    @tool
    def get_slack_messages(channel_id: str) -> str:
        """Get recent messages from a Slack channel by channel ID."""
        if not slack_token:
            return "Slack is not connected."
        client = WebClient(token=slack_token)
        users_response = client.users_list()
        user_map = {
            u["id"]: u.get("real_name") or u.get("name", u["id"])
            for u in users_response.get("members", [])
        }
        time.sleep(1)
        result = client.conversations_history(channel=channel_id, limit=10)
        messages = result.get("messages", [])
        if not messages:
            return "No messages"
        formatted = []
        for m in messages:
            name = user_map.get(m.get("user", ""), m.get("user", "unknown"))
            formatted.append(f"{name}: {m.get('text', '')}")
        return "\n".join(formatted)

    @tool
    def send_slack_message(channel_id: str, message: str) -> str:
        """Send a message to a Slack channel by channel ID."""
        if not slack_token:
            return "Slack is not connected."
        client = WebClient(token=slack_token)
        result = client.chat_postMessage(channel=channel_id, text=message)
        if result["ok"]:
            return f"Message sent to channel {channel_id}."
        return f"Failed to send message: {result.get('error')}"

    @tool
    def reply_to_slack_thread(channel_id: str, thread_ts: str, message: str) -> str:
        """Reply to a Slack thread. thread_ts is the timestamp of the parent message."""
        if not slack_token:
            return "Slack is not connected."
        client = WebClient(token=slack_token)
        result = client.chat_postMessage(
            channel=channel_id,
            text=message,
            thread_ts=thread_ts
        )
        if result["ok"]:
            return f"Reply sent to thread {thread_ts} in channel {channel_id}."
        return f"Failed to send reply: {result.get('error')}"

    @tool
    def search_slack_messages(query: str) -> str:
        """Search for messages containing a keyword across all Slack channels."""
        if not slack_token:
            return "Slack is not connected."
        client = WebClient(token=slack_token)
        users_response = client.users_list()
        user_map = {
            u["id"]: u.get("real_name") or u.get("name", u["id"])
            for u in users_response.get("members", [])
        }
        channels_response = client.conversations_list(types="public_channel,private_channel")
        channels = channels_response.get("channels", [])
        results = []
        for channel in channels:
            time.sleep(0.5)
            try:
                history = client.conversations_history(channel=channel["id"], limit=50)
                for m in history.get("messages", []):
                    if query.lower() in m.get("text", "").lower():
                        name = user_map.get(m.get("user", ""), m.get("user", "unknown"))
                        results.append(f"#{channel['name']} | {name}: {m.get('text', '')}")
            except Exception:
                continue
        return "\n".join(results) if results else f"No messages found containing '{query}'"

    @tool
    def get_slack_dms() -> str:
        """Get recent direct messages from Slack."""
        if not slack_token:
            return "Slack is not connected."
        client = WebClient(token=slack_token)
        users_response = client.users_list()
        user_map = {
            u["id"]: u.get("real_name") or u.get("name", u["id"])
            for u in users_response.get("members", [])
        }
        result = client.conversations_list(types="im")
        dms = result.get("channels", [])
        if not dms:
            return "No direct message conversations found."
        all_dms = []
        for dm in dms[:5]:
            time.sleep(0.5)
            history = client.conversations_history(channel=dm["id"], limit=5)
            messages = history.get("messages", [])
            other_user = user_map.get(dm.get("user", ""), dm.get("user", "unknown"))
            for m in messages:
                name = user_map.get(m.get("user", ""), m.get("user", "unknown"))
                all_dms.append(f"DM with {other_user} | {name}: {m.get('text', '')}")
        return "\n".join(all_dms) if all_dms else "No DM messages found."

    return [
        get_github_repos,
        get_github_issues,
        create_github_issue,
        close_github_issue,
        comment_on_github_issue,
        get_github_pull_requests,
        get_github_commits,
        get_unread_emails,
        get_email_body,
        search_emails,
        mark_email_as_read,
        send_email,
        reply_to_email,
        get_slack_channels,
        get_slack_messages,
        send_slack_message,
        reply_to_slack_thread,
        search_slack_messages,
        get_slack_dms,
    ]

def run_orchestrator(github_token, gmail_token, gmail_refresh_token, slack_token, message: str, gmail_expires_at: Optional[datetime] = None, on_gmail_refresh: Optional[Callable[[str, datetime], None]] = None):
    tools = make_orchestrator_tools(github_token, gmail_token, gmail_refresh_token, slack_token, gmail_expires_at=gmail_expires_at, on_gmail_refresh=on_gmail_refresh)
    llm_with_tools = llm.bind_tools(tools)
    tool_map = {t.name: t for t in tools}

    def agent_node(state: OrchestratorState):
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    def tool_node(state: OrchestratorState):
        from langchain_core.messages import ToolMessage
        last_message = state["messages"][-1]
        tool_messages = []
        for tool_call in last_message.tool_calls:
            try:
                result = tool_map[tool_call["name"]].invoke(tool_call["args"])
            except Exception as e:
                result = f"Tool '{tool_call['name']}' failed: {str(e)}. This service may need to be reconnected."
            tool_messages.append(
                ToolMessage(content=result, tool_call_id=tool_call["id"])
            )
        return {"messages": tool_messages}

    def should_continue(state: OrchestratorState):
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return END

    graph = StateGraph(OrchestratorState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    compiled = graph.compile()

    connected = []
    if github_token: connected.append("GitHub")
    if gmail_token: connected.append("Gmail")
    if slack_token: connected.append("Slack")

    system = SystemMessage(content=f"""You are FlowAgent, a powerful AI assistant that can act across GitHub, Gmail, and Slack.
Currently connected services: {', '.join(connected) if connected else 'none'}.
Only use tools for connected services. If asked about a disconnected service, tell the user to connect it from the sidebar.
Never ask the user for credentials. Always use your tools to get real data.""")

    result = compiled.invoke({
        "messages": [system, {"role": "user", "content": message}],
        "github_token": github_token,
        "gmail_token": gmail_token,
        "gmail_refresh_token": gmail_refresh_token,
        "gmail_expires_at": gmail_expires_at,
        "slack_token": slack_token,
        "output": ""
    })

    return result["messages"][-1].content