from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
import os
from uw_models import uw_tools
from langgraph.graph import MessagesState

uw_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a Medicare Supplement underwriting assistant for internal agents."
            "Use tools to answer the questions; do not create new underwriting rules."
            "Explain"
            "- Whether this sounds like Open Enrollment, Guaranteed Issue, or Underwritten"
            "- Any key considerations or typical knock-out conditions"
            "- If more details (dates, prior coverage, health history) are needed, explicitly say so."
            "Do not promise approval; say 'typically' or 'subject to underwriting review'.",
        ),
        MessagesPlaceholder(variable_name="uw_messages"),
    ]
)

uw_llm = ChatOpenAI(model=os.environ.get("GPT_MODEL"), temperature=0, api_key=os.environ.get("OPENAI_API_KEY")).bind_tools(uw_tools)
uw_chain = uw_prompt | uw_llm