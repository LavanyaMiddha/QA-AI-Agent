"""LangGraph node — single Gemini chat step."""

from functools import lru_cache

from langchain_core.messages import AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import MessagesState

from backend.config import settings


@lru_cache(maxsize=1)
def get_chat_model() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=settings.chat_model,
        google_api_key=settings.google_api_key,
        temperature=0.7,
    )


def call_model(state: MessagesState) -> dict[str, list[AIMessage]]:
    response = get_chat_model().invoke(state["messages"])
    return {"messages": [response]}
