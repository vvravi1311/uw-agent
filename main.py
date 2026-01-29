import streamlit as st
import pandas as pd
from typing import Any, Dict, List
from uw_graph_flow import uw_flow, run_graph
from langchain_core.messages import BaseMessage, HumanMessage

from dotenv import load_dotenv
load_dotenv()
import os

os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGCHAIN_PROJECT"] = "uw-agent"

st.set_page_config(page_title="Agent Underwriting Helper", layout="centered")
st.title("Agent Underwriting Helper")

LAST = -1


def highlight_fired(row):
    color = "#ffe6e6" if row["outcome"] == "FIRED" else "white"
    return [f"background-color: {color}"] * len(row)

with st.sidebar:
    st.subheader("Session")
    if st.button("Clear chat", use_container_width=True):
        st.session_state.pop("messages", None)
        st.rerun()

# Adding an initial msg into the st session_state
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Ask me anything about Underwriting rules. I’ll check the UW rules and help you with analysis and cite the details on rules.",
            "audit": {
                "evaluatedAt": "2026-01-28T20:56:19.548508Z",
                "matchedRules": [
                    {
                        "ruleId": "R-600",
                        "outcome": "SKIPPED",
                        "details": "No continuous GI for GA"
                    },
                    {
                        "ruleId": "R-400",
                        "outcome": "FIRED",
                        "details": "Proceed to UW checks."
                    }
                ]
            },
        }
    ]

# displaying the messages of the session_state in ui
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("audit"):
            audit=msg["audit"]
            df = pd.DataFrame(audit["matchedRules"])
            st.dataframe(df.style.apply(highlight_fired, axis=1), use_container_width=True)

prompt = st.chat_input("Ask a question about Underwriting...")

if prompt:
    # add msg to session_state
    st.session_state.messages.append({"role": "user", "content": prompt, "audit": []})
    with st.chat_message("user"):
        st.markdown(prompt) #Display message in UI

    with st.chat_message("assistant"):
        try:
            with st.spinner("Retrieving docs and generating answer…"):
                result = run_graph(prompt)
                answer = str(result.get("answer", "")).strip() or "(No answer returned.)"
                uw_audit = result.get("uw_audit", {})
                st.markdown(answer)   # display the answer and audit information
                if uw_audit:
                    # audit = uw_audit["audit"]
                    df = pd.DataFrame(uw_audit["matchedRules"])
                    st.dataframe(df.style.apply(highlight_fired, axis=1), use_container_width=True)
                # append the assistant answer to session state
                st.session_state.messages.append(
                    {"role": "assistant", "content": answer, "audit": uw_audit}
                )
        except Exception as e:
            st.error("Failed to generate a response.")
            st.exception(e)



# if prompt:
#     with st.chat_message("user"):
#         st.markdown(prompt)
#
#     with st.chat_message("assistant"):
#         try:
#             with st.spinner("Retrieving docs and generating answer…"):
#                 # result = uw_flow.invoke({"messages": [HumanMessage(
#                 #     content="Evaluate the Medicare application. Its for state of Georgia, the start date of the medicare insurance is from 1st February 2026.")]})
#                 result = uw_flow.invoke({"messages": [HumanMessage(
#                     content=prompt)]})
#
#                 answer = result["messages"][LAST].content
#                 st.markdown(prompt + " ..............." + answer)
#                 # st.markdown("show some content")
#         except Exception as e:
#             st.error("Failed to generate a response.")
#             st.exception(e)