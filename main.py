import streamlit as st
from typing import Any, Dict, List
from uw_graph_flow import uw_flow
from langchain_core.messages import BaseMessage, HumanMessage

st.set_page_config(page_title="Agent Underwriting Helper", layout="centered")
st.title("Agent Underwriting Helper")

LAST = -1

with st.sidebar:
    st.subheader("Session")
    if st.button("Clear chat", use_container_width=True):
        st.session_state.pop("messages", None)
        st.rerun()

prompt = st.chat_input("Ask a question about Underwriting...")

if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Retrieving docs and generating answer…"):
                # result = uw_flow.invoke({"messages": [HumanMessage(
                #     content="Evaluate the Medicare application. Its for state of Georgia, the start date of the medicare insurance is from 1st February 2026.")]})
                result = uw_flow.invoke({"messages": [HumanMessage(
                    content=prompt)]})

                answer = result["messages"][LAST].content
                st.markdown(prompt + " ..............." + answer)
                # st.markdown("show some content")
        except Exception as e:
            st.error("Failed to generate a response.")
            st.exception(e)