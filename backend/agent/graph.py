"""Simple LangGraph: one Gemini chat node."""

from functools import lru_cache

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph

from backend.agent.nodes import call_model
from backend.agent.prompts import FORMAT_PROMPTS


def build_graph():
    workflow = StateGraph(MessagesState)
    workflow.add_node("agent", call_model)
    workflow.add_edge(START, "agent")
    workflow.add_edge("agent", END)
    return workflow.compile()


@lru_cache(maxsize=1)
def get_compiled_graph():
    return build_graph()


def generate_questions(
    topic: str,
    question_format: str,
    count: int = 3,
    additional_instructions: str | None = None,
) -> str:
    """Run the graph with a format-specific system prompt."""
    if question_format not in FORMAT_PROMPTS:
        raise ValueError(f"Unknown format: {question_format}")

    system_prompt = FORMAT_PROMPTS[question_format].format(count=count)
    user_content = f"Topic: {topic}"
    if additional_instructions:
        user_content += f"\n\nAdditional instructions:\n{additional_instructions}"

    graph = get_compiled_graph()
    result = graph.invoke(
        {
            "messages": [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_content),
            ]
        }
    )
    return result["messages"][-1].content
