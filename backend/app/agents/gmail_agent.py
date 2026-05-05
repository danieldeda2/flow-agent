from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from langchain.tools import tool
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator
import os
import base64

llm = ChatAnthropic(model="claude-sonnet-4-6")

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

class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    access_token: str
    refresh_token: str
    output: str

def make_gmail_tools(access_token: str, refresh_token: str):
    @tool
    def list_unread_emails() -> str:
        """List unread emails from Gmail inbox"""
        service = get_gmail_service(access_token, refresh_token)
        results = service.users().messages().list(
            userId="me",
            q="is:unread",
            maxResults=10
        ).execute()

        messages = results.get("messages", [])
        if not messages:
            return "No unread emails"

        emails = []
        for msg in messages:
            detail = service.users().messages().get(
                userId="me",
                id=msg["id"],
                format="metadata",
                metadataHeaders=["From", "Subject", "Date"]
            ).execute()

            headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
            emails.append(f"From: {headers.get('From', 'Unknown')} | Subject: {headers.get('Subject', 'No subject')} | Date: {headers.get('Date', 'Unknown')}")

        return "\n".join(emails)

    @tool
    def search_emails(query: str) -> str:
        """Search emails in Gmail by keyword or sender"""
        service = get_gmail_service(access_token, refresh_token)
        results = service.users().messages().list(
            userId="me",
            q=query,
            maxResults=5
        ).execute()

        messages = results.get("messages", [])
        if not messages:
            return f"No emails found for query: {query}"

        emails = []
        for msg in messages:
            detail = service.users().messages().get(
                userId="me",
                id=msg["id"],
                format="metadata",
                metadataHeaders=["From", "Subject", "Date"]
            ).execute()

            headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
            emails.append(f"From: {headers.get('From', 'Unknown')} | Subject: {headers.get('Subject', 'No subject')}")

        return "\n".join(emails)

    @tool
    def get_email_body(message_id: str) -> str:
        """Get the full body of a specific email by message ID"""
        service = get_gmail_service(access_token, refresh_token)
        detail = service.users().messages().get(
            userId="me",
            id=message_id,
            format="full"
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

        return body[:2000] if body else "Could not extract email body"

    return [list_unread_emails, search_emails, get_email_body]

def run_gmail_agent(access_token: str, refresh_token: str, message: str):
    tools = make_gmail_tools(access_token, refresh_token)
    llm_with_tools = llm.bind_tools(tools)
    tool_map = {t.name: t for t in tools}

    def agent_node(state: AgentState):
        messages = state["messages"]
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def tool_node(state: AgentState):
        from langchain_core.messages import ToolMessage
        messages = state["messages"]
        last_message = messages[-1]

        tool_messages = []
        for tool_call in last_message.tool_calls:
            result = tool_map[tool_call["name"]].invoke(tool_call["args"])
            tool_messages.append(
                ToolMessage(content=result, tool_call_id=tool_call["id"])
            )
        return {"messages": tool_messages}

    def should_continue(state: AgentState):
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return END

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    compiled = graph.compile()

    system = SystemMessage(content="You are FlowAgent, an AI assistant that helps users manage their Gmail inbox. You can list unread emails, search emails, and read email contents. Never ask the user for credentials.")

    result = compiled.invoke({
        "messages": [system, {"role": "user", "content": message}],
        "access_token": access_token,
        "refresh_token": refresh_token,
        "output": ""
    })

    return result["messages"][-1].content