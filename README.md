# Q&A AI Agent

Exam question generator using a **simple LangGraph** workflow (single Gemini chat node) and **FastAPI**.

## Project layout

```
backend/
  config.py           # Settings from .env
  main.py             # FastAPI endpoints
  agent/
    prompts.py        # System prompts per question format
    nodes.py          # Gemini chat node
    graph.py          # Graph assembly + invoke helper
frontend/
  app.py              # Streamlit UI
```

## Setup

```bash
cd QA-AI-Agent
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
pip install -r frontend/requirements.txt
```

Create `.env` in the project root:

```
GOOGLE_API_KEY=your_key_here
CHAT_MODEL=gemini-2.5-flash
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,http://localhost:8501
```

## Run API

```bash
python -m backend.main
```

Or:

```bash
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Run from the **project root** (`QA-AI-Agent`), not from inside `backend/`.

## Streamlit UI

Terminal 1 — API:

```bash
python -m backend.main
```

Terminal 2 — frontend (either command works):

```bash
streamlit run frontend/app.py
```

Or:

```bash
python -m frontend.app
```

Open http://localhost:8501 (localhost only; see `.streamlit/config.toml`). Use the **Chat** tab for multi-turn conversations; history is stored in LangGraph's `MemorySaver` checkpointer by `thread_id`.

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check + configured model |
| POST | `/api/chat` | Multi-turn chat (`thread_id`, `message`, optional `question_format` on first turn) |
| GET | `/api/chat/{thread_id}` | Conversation history for a thread |
| POST | `/api/generate/essay` | Essay-style questions |
| POST | `/api/generate/short-answer` | Short-answer questions with model answers |
| POST | `/api/generate/mcq` | Multiple-choice questions |
| POST | `/api/generate/true-false` | True/false statements |

**Request body** (all generate endpoints):

```json
{
  "topic": "Photosynthesis",
  "count": 3,
  "additional_instructions": "High school biology, medium difficulty"
}
```

**Response:**

```json
{
  "topic": "Photosynthesis",
  "format": "mcq",
  "count": 3,
  "content": "1. ..."
}
```

Example:

```bash
curl -X POST http://localhost:8000/api/generate/mcq ^
  -H "Content-Type: application/json" ^
  -d "{\"topic\": \"World War II\", \"count\": 2}"
```
