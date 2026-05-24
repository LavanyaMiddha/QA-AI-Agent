"""Streamlit UI for the QA AI Agent question generator."""

import requests
import streamlit as st

FORMAT_ENDPOINTS = {
    "Essay": "/api/generate/essay",
    "Short answer": "/api/generate/short-answer",
    "Multiple choice (MCQ)": "/api/generate/mcq",
    "True / False": "/api/generate/true-false",
}

DEFAULT_API_URL = "http://127.0.0.1:8000"


def check_health(api_url: str) -> tuple[bool, str]:
    try:
        response = requests.get(f"{api_url.rstrip('/')}/api/health", timeout=5)
        response.raise_for_status()
        data = response.json()
        return True, data.get("model", "unknown")
    except requests.RequestException as exc:
        return False, str(exc)


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
        detail = response.text
        try:
            detail = response.json().get("detail", detail)
        except ValueError:
            pass
        raise RuntimeError(detail)
    return response.json()


def main():
    st.set_page_config(page_title="QA AI Agent", page_icon="📝", layout="wide")
    st.title("QA AI Agent")
    st.caption("Generate exam questions with Gemini")

    with st.sidebar:
        st.header("Settings")
        api_url = st.text_input("API URL", value=DEFAULT_API_URL)
        ok, info = check_health(api_url)
        if ok:
            st.success(f"API connected ({info})")
        else:
            st.error("API unreachable")
            st.caption(f"Start the backend: `python -m backend.main`\n\n{info}")

    col1, col2 = st.columns([2, 1])
    with col1:
        topic = st.text_area(
            "Topic or source material",
            placeholder="e.g. Photosynthesis, or paste notes to base questions on",
            height=120,
        )
    with col2:
        question_format = st.selectbox("Question format", list(FORMAT_ENDPOINTS.keys()))
        count = st.number_input("Number of questions", min_value=1, max_value=20, value=3)
        additional = st.text_area(
            "Extra instructions (optional)",
            placeholder="Difficulty, grade level, focus areas…",
            height=80,
        )

    generate = st.button("Generate questions", type="primary", disabled=not ok)

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


if __name__ == "__main__":
    main()
