"""
FastAPI backend for AskAI only.

Run (from project root):
  C:\\WORK\\goodSassDashboard2\\01_myENV\\Scripts\\python.exe -m uvicorn main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import traceback

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent import get_askai_service
from askai_verbose import vlog, vlog_error
from config import get_settings
from db import test_db_connection
from ollama_health import check_ollama_health

settings = get_settings()

if settings.askai_verbose:
    vlog("Verbose CMD logging ON (set ASKAI_VERBOSE=false in backend/.env to disable)")

app = FastAPI(
    title="GoodSaaS AskAI API",
    description="AskAI chat endpoint — single-call text2SQL (Ollama + SQL Server).",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    response: str
    source: str = "sql-chain-v2"


class HealthResponse(BaseModel):
    status: str
    ollama_model: str
    ollama_base_url: str
    ollama_connected: bool
    ollama_model_installed: bool
    ollama_model_loaded: bool
    ollama_running_models: list[str]
    ollama_message: str
    db_configured: bool
    db_connected: bool
    db_message: str
    message: str


@app.get("/api/ask-ai/health", response_model=HealthResponse)
def health() -> HealthResponse:
    db_connected, db_message = test_db_connection()
    ollama = check_ollama_health(settings)
    return HealthResponse(
        status="ok",
        ollama_model=settings.ollama_model,
        ollama_base_url=settings.ollama_base_url,
        ollama_connected=ollama.ollama_connected,
        ollama_model_installed=ollama.ollama_model_installed,
        ollama_model_loaded=ollama.ollama_model_loaded,
        ollama_running_models=ollama.ollama_running_models,
        ollama_message=ollama.ollama_message,
        db_configured=settings.db_configured,
        db_connected=db_connected,
        db_message=db_message,
        message="AskAI API is running. Use /api/ask-ai/chat for questions.",
    )


@app.post("/api/ask-ai/chat", response_model=ChatResponse)
def ask_ai_chat(payload: ChatRequest) -> ChatResponse:
    vlog(f"HTTP POST /api/ask-ai/chat")
    try:
        answer = get_askai_service().ask(payload.question)
        return ChatResponse(response=answer)
    except RuntimeError as exc:
        vlog_error("Service unavailable", exc)
        if settings.askai_verbose:
            traceback.print_exc()
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        vlog_error("AskAI failed", exc)
        if settings.askai_verbose:
            traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"AskAI failed: {exc}") from exc


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "ask-ai", "docs": "/docs"}
