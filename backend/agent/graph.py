"""Simple LangGraph: one Gemini chat node with checkpointed memory."""

import uuid
from functools import lru_cache
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph

from backend.agent.nodes import call_model
from backend.agent.prompts import CHAT_SYSTEM, FORMAT_PROMPTS


def _thread_config(thread_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": thread_id}}


def message_to_dict(message: BaseMessage) -> dict[str, str]:
    if isinstance(message, HumanMessage):
        role = "human"
    elif isinstance(message, SystemMessage):
        role = "system"
    elif isinstance(message, AIMessage):
        role = "ai"
    else:
        role = getattr(message, "type", "ai")
    content = message.content if isinstance(message.content, str) else str(message.content)
    return {"role": role, "content": content}


@lru_cache(maxsize=1)
def get_checkpointer() -> MemorySaver:
    return MemorySaver()


def build_graph() -> StateGraph:
    workflow = StateGraph(MessagesState)
    workflow.add_node("agent", call_model)
    workflow.add_edge(START, "agent")
    workflow.add_edge("agent", END)
    return workflow


@lru_cache(maxsize=1)
def get_compiled_graph():
    return build_graph().compile(checkpointer=get_checkpointer())


def get_thread_messages(thread_id: str, *, include_system: bool = False) -> list[dict[str, str]]:
    graph = get_compiled_graph()
    snapshot = graph.get_state(_thread_config(thread_id))
    messages = snapshot.values.get("messages") or []
    serialized = [message_to_dict(message) for message in messages]
    if include_system:
        return serialized
    return [message for message in serialized if message["role"] != "system"]


def chat_turn(
    thread_id: str,
    message: str,
    question_format: str | None = None,
    count: int = 3,
) -> tuple[str, list[dict[str, str]]]:
    """Append a user turn to a checkpointed thread and return the assistant reply."""
    graph = get_compiled_graph()
    config = _thread_config(thread_id)
    snapshot = graph.get_state(config)
    existing = snapshot.values.get("messages") or []

    new_messages: list[BaseMessage] = []
    if not existing:
        if question_format:
            if question_format not in FORMAT_PROMPTS:
                raise ValueError(f"Unknown format: {question_format}")
            new_messages.append(SystemMessage(content=FORMAT_PROMPTS[question_format].format(count=count)))
        else:
            new_messages.append(SystemMessage(content=CHAT_SYSTEM))
    new_messages.append(HumanMessage(content=message))

    result = graph.invoke({"messages": new_messages}, config=config)
    reply = result["messages"][-1].content
    return reply, get_thread_messages(thread_id)


def generate_questions(
    topic: str,
    question_format: str,
    count: int = 3,
    additional_instructions: str | None = None,
) -> str:
    """One-shot generation in an isolated checkpoint thread."""
    if question_format not in FORMAT_PROMPTS:
        raise ValueError(f"Unknown format: {question_format}")

    system_prompt = FORMAT_PROMPTS[question_format].format(count=count)
    user_content = f"Topic: {topic}"
    if additional_instructions:
        user_content += f"\n\nAdditional instructions:\n{additional_instructions}"

    graph = get_compiled_graph()
    thread_id = f"generate-{uuid.uuid4()}"
    result = graph.invoke(
        {
            "messages": [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_content),
            ]
        },
        config=_thread_config(thread_id),
    )
    return result["messages"][-1].content
