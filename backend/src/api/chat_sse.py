"""Standalone FastAPI service for RootLink chat and archives."""

import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal, Optional

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from src.agents.agent import build_agent
from src.storage.supabase import (
    authenticated_user,
    load_archive,
    record_visit,
    save_archive,
)
from src.utils.sse_handler import SSEHandler, stream_agent_response_sync


load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def normalize_lang(lang: Optional[str]) -> Literal["zh", "en"]:
    return "en" if lang == "en" else "zh"


def thread_id_for(user_id: str, lang: str) -> str:
    return f"{user_id}_{normalize_lang(lang)}"


def configured_origins() -> list[str]:
    value = os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:3000,http://localhost:5173,http://127.0.0.1:5500,"
        "https://getrootlink.com,https://www.getrootlink.com",
    )
    return [origin.strip() for origin in value.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.agents = {
        "zh": build_agent(lang="zh"),
        "en": build_agent(lang="en"),
    }
    yield


app = FastAPI(title="RootLink API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


class ChatRequest(BaseModel):
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    message: str = Field(min_length=1)
    lang: str = "zh"


class ArchiveRequest(BaseModel):
    data: dict


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/chat/sse")
async def chat_with_sse(
    payload: ChatRequest,
    request: Request,
    background_tasks: BackgroundTasks,
):
    user_id = payload.user_id or payload.session_id or f"anonymous_{uuid.uuid4().hex[:12]}"
    lang = normalize_lang(payload.lang)
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="message must not be empty")

    client_ip = request.client.host if request.client else "unknown"
    background_tasks.add_task(record_visit, client_ip, user_id)
    agent = request.app.state.agents[lang]

    return StreamingResponse(
        stream_agent_response_sync(
            agent=agent,
            messages=[HumanMessage(content=message)],
            config={"configurable": {"thread_id": thread_id_for(user_id, lang)}},
            lang=lang,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/chat/json")
async def chat_with_json(payload: ChatRequest, request: Request):
    user_id = payload.user_id or payload.session_id or f"anonymous_{uuid.uuid4().hex[:12]}"
    lang = normalize_lang(payload.lang)
    response = request.app.state.agents[lang].invoke(
        {"messages": [HumanMessage(content=payload.message.strip())]},
        config={"configurable": {"thread_id": thread_id_for(user_id, lang)}},
    )
    messages = response.get("messages", []) if isinstance(response, dict) else []
    content = messages[-1].content if messages else str(response)
    handler = SSEHandler()
    return handler.sanitize_structured_data(
        handler.parse_structured_data(content if isinstance(content, str) else str(content)),
        lang,
    )


@app.post("/api/archive/save")
async def archive_save(payload: ArchiveRequest, request: Request):
    user = await authenticated_user(request)
    user_id = user.get("email") or user.get("id")
    await save_archive(user_id, payload.data)
    return {"ok": True}


@app.post("/api/archive/load")
async def archive_load(request: Request):
    user = await authenticated_user(request)
    user_id = user.get("email") or user.get("id")
    return {"data": await load_archive(user_id)}
