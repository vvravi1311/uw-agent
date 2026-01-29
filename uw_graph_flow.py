from typing import TypedDict, Annotated, Any, Dict
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
from langgraph.graph import MessagesState, StateGraph,END
import json

from langgraph.prebuilt import ToolNode
load_dotenv()
import os

from uw_chains import uw_chain
from uw_rules_engine import uw_tools

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


def has_tool_message(result):
    # Case 1: result is a single message
    if hasattr(result, "tool_calls") and result.tool_calls:
        return True

    # Case 2: result is a dict with messages
    if isinstance(result, dict) and "messages" in result:
        for msg in result["messages"]:
            if getattr(msg, "type", None) == "tool":
                return True
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                return True
    return False


def run_graph(query: str) -> Dict[str, Any]:
    result = uw_flow.invoke({"messages": [HumanMessage(
        content=query)]})
    answer = result["messages"][LAST].content
    audit = {}
    if has_tool_message(result):
        tool_msg = next(msg for msg in result["messages"] if isinstance(msg, ToolMessage))
        audit = json.loads(tool_msg.content)["audit"]
    return {
        "answer": answer,
        "uw_audit": audit
    }

if __name__ == "__main__":
    print("Hello ReAct LangGraph with Function Calling")
    # res = uw_flow.invoke({"messages": [HumanMessage(content="Evaluate the Medicare application. Its for state of Georgia, the start date of the medicare insurance is from 1st February 2026.")]})
    # # res = uw_flow.invoke({"messages": [HumanMessage(content="An agent is helping a 67‑year‑old applicant who: Just left an employer group plan last month Has several health conditions (COPD, diabetes, uses insulin) Wants to enroll in Medigap Plan G Has been on Medicare Part B for 18 months Has no recent GI events except losing employer coverage Has a hospitalization 45 days ago Uses oxygen at night")]})
    # # res = uw_flow.invoke({"messages": [HumanMessage(content="hi ")]})
    # tool_msg = next(msg for msg in res["messages"] if isinstance(msg, ToolMessage))
    # # tool_txt = tool_msg[0]  # your ToolMessage inside the list
    # audit = json.loads(tool_msg.content)["audit"]
    # print(res["messages"][LAST].content)
    query = "Evaluate the Medicare application. Its for state of Georgia, the start date of the medicare insurance is from 1st February 2026."
    result = run_graph(query)
    print(result["answer"])
    print("***                                        **")
    print("*********************************  **********")
    print(result["uw_audit"])
    print(json.dumps(result["uw_audit"], indent=2))
    # print(json.dumps(json.loads(str(result["uw_audit"])), indent=2))

