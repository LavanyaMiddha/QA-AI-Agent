"""Streamlit UI for the QA AI Agent question generator."""

import uuid

import requests
import streamlit as st

FORMAT_ENDPOINTS = {
    "Essay": "/api/generate/essay",
    "Short answer": "/api/generate/short-answer",
    "Multiple choice (MCQ)": "/api/generate/mcq",
    "True / False": "/api/generate/true-false",
}

FORMAT_KEYS = {
    "Essay": "essay",
    "Short answer": "short_answer",
    "Multiple choice (MCQ)": "mcq",
    "True / False": "true_false",
}

GENERAL = "General chat"
FORMAT_OPTIONS = [GENERAL] + list(FORMAT_ENDPOINTS.keys())

DEFAULT_API_URL = "http://127.0.0.1:8000"


def init_session_state() -> None:
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())
    if "messages" not in st.session_state:
        st.session_state.messages = []


def reset_conversation() -> None:
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.messages = []


def check_health(api_url: str) -> tuple[bool, str]:
    try:
        response = requests.get(f"{api_url.rstrip('/')}/api/health", timeout=5)
        response.raise_for_status()
        data = response.json()
        return True, data.get("model", "unknown")
    except requests.RequestException as exc:
        return False, str(exc)


def _parse_error(response: requests.Response) -> str:
    detail = response.text
    try:
        detail = response.json().get("detail", detail)
    except ValueError:
        pass
    return detail


def fetch_thread_history(api_url: str, thread_id: str) -> list[dict]:
    response = requests.get(f"{api_url.rstrip('/')}/api/chat/{thread_id}", timeout=10)
    if not response.ok:
        raise RuntimeError(_parse_error(response))
    return response.json()["messages"]


def send_chat_message(
    api_url: str,
    thread_id: str,
    message: str,
    question_format: str | None,
    count: int,
) -> dict:
    payload = {
        "thread_id": thread_id,
        "message": message,
        "count": count,
    }
    if question_format:
        payload["question_format"] = question_format

    response = requests.post(
        f"{api_url.rstrip('/')}/api/chat",
        json=payload,
        timeout=120,
    )
    if not response.ok:
        raise RuntimeError(_parse_error(response))
    return response.json()


def generate_questions(
    api_url: str,
    endpoint: str,
    topic: str,
    count: int,
    additional_instructions: str | None,
) -> dict:
    payload = {"topic": topic, "count": count}
    if additional_instructions and additional_instructions.strip():
        payload["additional_instructions"] = additional_instructions.strip()

    response = requests.post(
        f"{api_url.rstrip('/')}{endpoint}",
        json=payload,
        timeout=120,
    )
    if not response.ok:
        raise RuntimeError(_parse_error(response))
    return response.json()


def render_chat_tab(api_url: str, api_ok: bool) -> None:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if not api_ok:
        st.info("Connect to the API to start chatting.")
        return

    prompt = st.chat_input("Ask for questions or follow up on prior ones…")
    if not prompt:
        return

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    format_label = st.session_state.get("chat_format", GENERAL)
    count = st.session_state.get("chat_count", 3)
    question_format = None if format_label == GENERAL else FORMAT_KEYS[format_label]
    is_new_thread = len(st.session_state.messages) == 1

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            try:
                result = send_chat_message(
                    api_url=api_url,
                    thread_id=st.session_state.thread_id,
                    message=prompt,
                    question_format=question_format if is_new_thread else None,
                    count=count,
                )
            except RuntimeError as exc:
                st.error(str(exc))
                st.session_state.messages.pop()
                return
            except requests.RequestException as exc:
                st.error(f"Could not reach API: {exc}")
                st.session_state.messages.pop()
                return

            st.markdown(result["reply"])
            st.session_state.messages = [
                {
                    "role": "assistant" if message["role"] == "ai" else "user",
                    "content": message["content"],
                }
                for message in result["messages"]
            ]


def render_generate_tab(api_url: str, api_ok: bool) -> None:
    col1, col2 = st.columns([2, 1])
    with col1:
        topic = st.text_area(
            "Topic or source material",
            placeholder="e.g. Photosynthesis, or paste notes to base questions on",
            height=120,
        )
    with col2:
        question_format = st.selectbox("Question format", list(FORMAT_ENDPOINTS.keys()), key="gen_format")
        count = st.number_input("Number of questions", min_value=1, max_value=20, value=3, key="gen_count")
        additional = st.text_area(
            "Extra instructions (optional)",
            placeholder="Difficulty, grade level, focus areas…",
            height=80,
            key="gen_extra",
        )

    generate = st.button("Generate questions", type="primary", disabled=not api_ok, key="gen_btn")

    if generate:
        if not topic or not topic.strip():
            st.warning("Please enter a topic.")
            return

        endpoint = FORMAT_ENDPOINTS[question_format]
        with st.spinner("Generating…"):
            try:
                result = generate_questions(
                    api_url=api_url,
                    endpoint=endpoint,
                    topic=topic.strip(),
                    count=count,
                    additional_instructions=additional,
                )
            except RuntimeError as exc:
                st.error(f"Generation failed: {exc}")
                return
            except requests.RequestException as exc:
                st.error(f"Could not reach API: {exc}")
                return

        st.subheader("Generated questions")
        st.markdown(result["content"])

        with st.expander("Response details"):
            st.json(result)


def main():
    st.set_page_config(page_title="QA AI Agent", page_icon="📝", layout="wide")
    st.title("QA AI Agent")
    st.caption("Generate exam questions with Gemini")

    init_session_state()

    with st.sidebar:
        st.header("Settings")
        api_url = st.text_input("API URL", value=DEFAULT_API_URL)
        ok, info = check_health(api_url)
        if ok:
            st.success(f"API connected ({info})")
        else:
            st.error("API unreachable")
            st.caption(f"Start the backend: `python -m backend.main`\n\n{info}")

        st.divider()
        st.subheader("Chat")
        st.session_state.chat_format = st.selectbox(
            "Format (first message only)",
            FORMAT_OPTIONS,
            help="Applied when you start a new conversation.",
        )
        st.session_state.chat_count = st.number_input(
            "Default count (first message)",
            min_value=1,
            max_value=20,
            value=st.session_state.get("chat_count", 3),
        )

        if st.button("New conversation", disabled=not ok):
            reset_conversation()
            st.rerun()

        if st.button("Sync from server", disabled=not ok):
            try:
                st.session_state.messages = [
                    {
                        "role": "assistant" if message["role"] == "ai" else "user",
                        "content": message["content"],
                    }
                    for message in fetch_thread_history(api_url, st.session_state.thread_id)
                ]
                st.success("History synced.")
            except RuntimeError as exc:
                st.warning(str(exc))

        st.caption(f"Thread: `{st.session_state.thread_id[:8]}…`")

    chat_tab, generate_tab = st.tabs(["Chat", "Quick generate"])

    with chat_tab:
        render_chat_tab(api_url, ok)

    with generate_tab:
        render_generate_tab(api_url, ok)


def _is_streamlit_runtime() -> bool:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        return get_script_run_ctx() is not None
    except Exception:
        return False


def run() -> None:
    """Launch the Streamlit server for this app."""
    import sys

    from streamlit.web import cli as stcli

    sys.argv = ["streamlit", "run", str(__file__), *sys.argv[1:]]
    sys.exit(stcli.main())


if __name__ == "__main__":
    if _is_streamlit_runtime():
        main()
    else:
        run()
