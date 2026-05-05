from langgraph.graph import StateGraph, END
from langchain_anthropic import ChatAnthropic
from langchain.tools import tool
from langchain_core.messages import SystemMessage
from typing import TypedDict, Annotated
import operator
import requests

llm = ChatAnthropic(model="claude-sonnet-4-6")

class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    access_token: str
    output: str

def make_tools(access_token: str):
    @tool
    def list_repos() -> str:
        """List all GitHub repositories for the authenticated user"""
        response = requests.get(
            "https://api.github.com/user/repos",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json"
            }
        )
        repos = [r["name"] for r in response.json()]
        return f"Repositories: {', '.join(repos)}"

    @tool
    def get_repo_issues(repo_name: str) -> str:
        """Get open issues for a specific GitHub repository"""
        response = requests.get(
            f"https://api.github.com/repos/{repo_name}/issues",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json"
            }
        )
        if response.status_code != 200:
            return f"Could not fetch issues for {repo_name}"
        issues = [f"#{i['number']}: {i['title']}" for i in response.json()]
        return f"Open issues: {', '.join(issues)}" if issues else "No open issues"

    return [list_repos, get_repo_issues]

def run_agent(access_token: str, message: str):
    tools = make_tools(access_token)
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

    system = SystemMessage(content="You are FlowAgent, an AI assistant that helps users manage their GitHub repositories. You have access to their GitHub account and can list repos and check issues. Never ask the user for credentials.")

    result = compiled.invoke({
        "messages": [system, {"role": "user", "content": message}],
        "access_token": access_token,
        "output": ""
    })

    return result["messages"][-1].content