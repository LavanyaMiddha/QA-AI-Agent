"""FastAPI — question generation via a simple LangGraph + Gemini agent."""

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.agent.graph import generate_questions, get_compiled_graph
from backend.config import settings


app = FastAPI(
    title="QA AI Agent",
    description="Generate exam questions (essay, short answer, MCQ, true/false) with Gemini",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    topic: str = Field(..., min_length=1, description="Subject or material to base questions on")
    count: int = Field(default=3, ge=1, le=20, description="Number of questions to generate")
    additional_instructions: str | None = Field(
        default=None,
        description="Optional extra guidance (difficulty, audience, style, etc.)",
    )


class GenerateResponse(BaseModel):
    topic: str
    format: str
    count: int
    content: str


class HealthResponse(BaseModel):
    status: str
    model: str


def _require_api_key() -> None:
    if not settings.google_api_key:
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY is not configured")


def _generate(format_key: str, body: GenerateRequest) -> GenerateResponse:
    _require_api_key()
    get_compiled_graph()
    try:
        content = generate_questions(
            topic=body.topic,
            question_format=format_key,
            count=body.count,
            additional_instructions=body.additional_instructions,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Generation failed: {exc}") from exc

    return GenerateResponse(
        topic=body.topic,
        format=format_key,
        count=body.count,
        content=content,
    )


@app.get("/api/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", model=settings.chat_model)


@app.post("/api/generate/essay", response_model=GenerateResponse)
async def generate_essay(body: GenerateRequest):
    return _generate("essay", body)


@app.post("/api/generate/short-answer", response_model=GenerateResponse)
async def generate_short_answer(body: GenerateRequest):
    return _generate("short_answer", body)


@app.post("/api/generate/mcq", response_model=GenerateResponse)
async def generate_mcq(body: GenerateRequest):
    return _generate("mcq", body)


@app.post("/api/generate/true-false", response_model=GenerateResponse)
async def generate_true_false(body: GenerateRequest):
    return _generate("true_false", body)


def run():
    uvicorn.run(
        "backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )


if __name__ == "__main__":
    run()
