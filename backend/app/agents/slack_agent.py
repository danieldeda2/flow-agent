from slack_sdk import WebClient
from langchain.tools import tool
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator

llm = ChatAnthropic(model="claude-sonnet-4-6")

class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    access_token: str
    output: str

def make_slack_tools(access_token: str):
    client = WebClient(token=access_token)

    @tool
    def list_channels() -> str:
        """List all Slack channels the user has access to"""
        result = client.conversations_list(types="public_channel,private_channel")
        channels = [f"#{c['name']} (id: {c['id']})" for c in result["channels"]]
        return f"Channels: {', '.join(channels)}" if channels else "No channels found"

    @tool
    def get_channel_messages(channel_id: str) -> str:
        """Get recent messages from a Slack channel by channel ID"""
        result = client.conversations_history(channel=channel_id, limit=10)
        messages = result.get("messages", [])
        if not messages:
            return "No messages found"

        output = []
        for msg in messages:
            user = msg.get("user", "unknown")
            text = msg.get("text", "")
            output.append(f"User {user}: {text}")

        return "\n".join(output)

    @tool
    def get_direct_messages() -> str:
        """Get recent direct message conversations"""
        result = client.conversations_list(types="im")
        ims = result.get("channels", [])
        if not ims:
            return "No direct message conversations found"

        output = []
        for im in ims[:5]:
            history = client.conversations_history(channel=im["id"], limit=3)
            messages = history.get("messages", [])
            for msg in messages:
                text = msg.get("text", "")
                if text:
                    output.append(f"DM: {text}")

        return "\n".join(output) if output else "No direct messages found"

    return [list_channels, get_channel_messages, get_direct_messages]

def run_slack_agent(access_token: str, message: str):
    tools = make_slack_tools(access_token)
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

    system = SystemMessage(content="You are FlowAgent, an AI assistant that helps users manage their Slack workspace. You can list channels, read messages, and check direct messages. Never ask the user for credentials.")

    result = compiled.invoke({
        "messages": [system, {"role": "user", "content": message}],
        "access_token": access_token,
        "output": ""
    })

    return result["messages"][-1].content