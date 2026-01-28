from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
from langgraph.graph import MessagesState, StateGraph,END

from langgraph.prebuilt import ToolNode
load_dotenv()

from uw_chains import uw_chain
from uw_models import uw_tools

UW_AGENT_REASON="uw_agent_reason"
UW_TOOL_NODE= "uw_tool_node"

LAST = -1

class MessageGraph(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

def uw_agent_reason(state: MessageGraph):
    return {"messages": [uw_chain.invoke({"uw_messages": state["messages"]})]}

uw_tool_node = ToolNode(uw_tools)

def should_continue(state: MessagesState) -> str:
    if not state["messages"][LAST].tool_calls:
        return END
    return UW_TOOL_NODE

flow = StateGraph(MessagesState)
flow.add_node(UW_AGENT_REASON, uw_agent_reason)
flow.add_node(UW_TOOL_NODE, uw_tool_node)

flow.set_entry_point(UW_AGENT_REASON)
flow.add_conditional_edges(UW_AGENT_REASON, should_continue, {
    END:END,
    UW_TOOL_NODE:UW_TOOL_NODE})
flow.add_edge(UW_TOOL_NODE, UW_AGENT_REASON)

uw_flow = flow.compile()
uw_flow.get_graph().draw_mermaid_png(output_file_path="uw_flow.png")

if __name__ == "__main__":
    print("Hello ReAct LangGraph with Function Calling")
    res = uw_flow.invoke({"messages": [HumanMessage(content="Evaluate the Medicare application. Its for state of Georgia, the start date of the medicare insurance is from 1st February 2026.")]})
    # res = uw_flow.invoke({"messages": [HumanMessage(content="Evaluate the Medicare application. Its for state of Georgia")]})

    print(res["messages"][LAST].content)
