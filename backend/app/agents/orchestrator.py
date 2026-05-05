from langchain_anthropic import ChatAnthropic
from langchain.tools import tool
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator
import requests
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from slack_sdk import WebClient
import base64
import os

llm = ChatAnthropic(model="claude-sonnet-4-6")

class OrchestratorState(TypedDict):
    messages: Annotated[list, operator.add]
    github_token: str
    gmail_token: str
    gmail_refresh_token: str
    slack_token: str
    output: str

def get_gmail_service(access_token: str, refresh_token: str):
    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        scopes=["https://www.googleapis.com/auth/gmail.readonly"]
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("gmail", "v1", credentials=creds)

def make_orchestrator_tools(github_token: str, gmail_token: str, gmail_refresh_token: str, slack_token: str):

    @tool
    def get_github_repos() -> str:
        """Get all GitHub repositories for the user. Returns repo names and owner username."""
        response = requests.get(
            "https://api.github.com/user/repos",
            headers={"Authorization": f"Bearer {github_token}"}
        )
        user_response = requests.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {github_token}"}
        )
        username = user_response.json().get("login", "unknown")
        repos = [r["name"] for r in response.json()]
        return f"GitHub username: {username}\nRepositories: {', '.join(repos)}"
        
    @tool
    def get_github_issues(repo_name: str) -> str:
        """Get open issues for a GitHub repository"""
        response = requests.get(
            f"https://api.github.com/repos/{repo_name}/issues",
            headers={"Authorization": f"Bearer {github_token}"}
        )
        if response.status_code != 200:
            return f"Could not fetch issues for {repo_name}"
        issues = [f"#{i['number']}: {i['title']}" for i in response.json()]
        return f"Issues: {', '.join(issues)}" if issues else "No open issues"

    @tool
    def create_github_issue(repo_name: str, title: str, body: str) -> str:
        """Create a new issue in a GitHub repository. Use the exact repo name from get_github_repos."""
        user_response = requests.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {github_token}"}
        )
        username = user_response.json().get("login")
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
    def get_unread_emails() -> str:
        """Get unread emails from Gmail. Returns message IDs and metadata."""
        service = get_gmail_service(gmail_token, gmail_refresh_token)
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
        """Get the full body of a specific email. message_id must be the Gmail MESSAGE_ID value from get_unread_emails, NOT an email address."""
        service = get_gmail_service(gmail_token, gmail_refresh_token)
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
    def get_slack_channels() -> str:
        """Get all Slack channels"""
        client = WebClient(token=slack_token)
        result = client.conversations_list(types="public_channel,private_channel")
        channels = [f"#{c['name']} (id: {c['id']})" for c in result["channels"]]
        return f"Channels: {', '.join(channels)}"

    @tool
    def get_slack_messages(channel_id: str) -> str:
        """Get recent messages from a Slack channel"""
        client = WebClient(token=slack_token)
        result = client.conversations_history(channel=channel_id, limit=10)
        messages = result.get("messages", [])
        if not messages:
            return "No messages"
        return "\n".join([f"User {m.get('user', 'unknown')}: {m.get('text', '')}" for m in messages])

    return [
        get_github_repos,
        get_github_issues,
        create_github_issue,
        get_unread_emails,
        get_email_body,
        get_slack_channels,
        get_slack_messages,
    ]

def run_orchestrator(github_token: str, gmail_token: str, gmail_refresh_token: str, slack_token: str, message: str):
    tools = make_orchestrator_tools(github_token, gmail_token, gmail_refresh_token, slack_token)
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

    system = SystemMessage(content="""You are FlowAgent, a powerful AI assistant that can act across GitHub, Gmail, and Slack simultaneously.
You have access to all three services at once and can perform complex cross-service tasks.
Examples of what you can do:
- Read emails and create GitHub issues from them
- Summarize Slack activity and email updates together
- Check GitHub issues and cross-reference with emails about them
Never ask the user for credentials. Always use your tools to get real data.""")

    result = compiled.invoke({
        "messages": [system, {"role": "user", "content": message}],
        "github_token": github_token,
        "gmail_token": gmail_token,
        "gmail_refresh_token": gmail_refresh_token,
        "slack_token": slack_token,
        "output": ""
    })

    return result["messages"][-1].content