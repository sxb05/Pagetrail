import logging
import re
import uuid
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from agent import get_agent
from auth import CurrentUser, router as auth_router
from db import (
    conversation_belongs_to_user,
    create_update_convo,
    delete_conversation,
    get_chat_history,
    init_db,
    list_conversations,
    save_chat_message,
)
from rag import (
    add_document_to_vector_store,
    retrieve_documents,
    init_rag_db,
)
from tools import set_current_thid

logger = logging.getLogger(__name__)


import os

cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

app = FastAPI(title="PageTrail")
app.include_router(auth_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


FRONTEND = Path(__file__).parent / "frontend" / "dist"
BRAND_ICON = Path(__file__).parent / "frontend" / "pagetrail-icon.png"
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
MAX_UPLOAD_SIZE = 10 * 1024 * 1024


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_error_handler(_request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.exception("Database error", exc_info=exc)
    return JSONResponse(
        status_code=503,
        content={"detail": "The database is temporarily unavailable. Please try again."},
    )


@app.on_event("startup")
def startup() -> None:
    # Create the RAG table before init_db enables RLS on it.
    init_rag_db()
    init_db()

    
@app.get("/")
async def root_to_login():
    return RedirectResponse(url="/login")

def user_login() -> dict[str, str]:
    return {"message": "Login endpoint placeholder"} 
@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

class ChatRequest(BaseModel):
    thread_id: str
    message: str = Field(min_length=1, max_length=20_000)
    model: str = "gemini-3.1-flash-lite"


def message_content(message: Any) -> str:
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
                continue
            if not isinstance(part, dict):
                continue
            if part.get("type") in {"thinking", "thought"} or "thought" in part:
                continue
            text = part.get("text")
            if isinstance(text, str):
                parts.append(text)
        return "".join(parts)
    return str(content) if content is not None else ""


def clean_llm_output(text: str) -> str:
    cleaned = text.replace("\r\n", "\n").strip()
    cleaned = re.sub(r"<think(?:ing)?>[\s\S]*?</think(?:ing)?>", "", cleaned, flags=re.I)
    cleaned = re.sub(r"</?think(?:ing)?>", "", cleaned, flags=re.I)
    fenced = re.fullmatch(r"```(?:markdown|md|text)?\s*\n([\s\S]*?)\n```", cleaned)
    if fenced:
        cleaned = fenced.group(1).strip()
    cleaned = re.sub(
        r"```(?:json)?\s*\{\s*\"(?:name|tool_calls|function)\"[\s\S]*?\}\s*```",
        "",
        cleaned,
        flags=re.I,
    )
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def last_assistant_text(messages: list[Any]) -> str:
    for message in reversed(messages):
        if getattr(message, "type", None) == "tool":
            continue
        text = clean_llm_output(message_content(message))
        if text:
            return text
    return "I was unable to produce a response. Please try again."


@app.get("/api/conversations")
def conversations(current_user: CurrentUser) -> list[dict[str, str]]:
    return [
        {
            "thread_id": conversation.thread_id,
            "name": conversation.name,
            "updated_at": conversation.updated_at,
        }
        for conversation in list_conversations(current_user.id)
    ]


@app.post("/api/conversations")
def new_conversation(current_user: CurrentUser) -> dict[str, str]:
    thread_id = str(uuid.uuid4())
    create_update_convo(thread_id, current_user.id, "", "New conversation")
    return {"thread_id": thread_id, "name": "New conversation"}


@app.get("/api/conversations/{thread_id}/messages")
def history(thread_id: str, current_user: CurrentUser) -> list[dict[str, str]]:
    return [
        {"role": message.role, "content": message.content}
        for message in get_chat_history(thread_id, current_user.id)
    ]


@app.delete("/api/conversations/{thread_id}")
def remove_conversation(thread_id: str, current_user: CurrentUser) -> dict[str, bool]:
    if not delete_conversation(thread_id, current_user.id):
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return {"deleted": True}


@app.post("/api/chat")
def chat(request: ChatRequest, current_user: CurrentUser) -> dict[str, str]:
    if not create_update_convo(
        request.thread_id, current_user.id, request.message, request.message[:48]
    ):
        raise HTTPException(status_code=404, detail="Conversation not found.")
    set_current_thid(request.thread_id)
    save_chat_message(request.thread_id, current_user.id, "user", request.message)

    try:
        document_context = retrieve_documents(request.message, request.thread_id, k=5)
        prompt = request.message
        if isinstance(document_context, list):
            context_text = "\n\n".join(
                f"[{item['metadata']['source']}]\n{item['content']}"
                for item in document_context
            )
            prompt = (
                "Use the following excerpts from the user's uploaded documents when "
                "answering the request. If the excerpts do not contain the answer, "
                "say so instead of inventing details.\n\n"
                f"{context_text}\n\nUser request: {request.message}"
            )
        agent = get_agent(request.model)
        result = agent.invoke(
            {"messages": [{"role": "user", "content": prompt}]},
            config={"configurable": {"thread_id": request.thread_id}},
        )
        answer = last_assistant_text(result["messages"])
    except Exception:
        logger.exception("Chat generation failed")
        raise HTTPException(
            status_code=502,
            detail="Unable to generate a response. Please try again.",
        ) from None

    save_chat_message(request.thread_id, current_user.id, "assistant", answer)
    return {"role": "assistant", "content": answer}


@app.post("/api/conversations/{thread_id}/files")
async def upload_file(
    thread_id: str, current_user: CurrentUser, file: UploadFile = File(...)
) -> dict[str, Any]:
    if not conversation_belongs_to_user(thread_id, current_user.id):
        raise HTTPException(status_code=404, detail="Conversation not found.")

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".pdf", ".docx", ".txt", ".md"}:
        raise HTTPException(status_code=400, detail="Upload a PDF, DOCX, TXT, or MD file.")

    destination = UPLOAD_DIR / f"{uuid.uuid4()}{suffix}"
    try:
        contents = await file.read(MAX_UPLOAD_SIZE + 1)
        if not contents:
            raise HTTPException(status_code=400, detail="The uploaded file is empty.")
        if len(contents) > MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=413,
                detail="The uploaded file must be smaller than 10 MB.",
            )

        destination.write_bytes(contents)
        result = add_document_to_vector_store(str(destination), thread_id)
        return result
    except HTTPException:
        raise
    except Exception:
        logger.exception("File indexing failed")
        raise HTTPException(
            status_code=422,
            detail="Unable to index file. Please try a different document.",
        ) from None
    finally:
        destination.unlink(missing_ok=True)
        await file.close()


def _frontend_file(path: str) -> Path | None:
    root = FRONTEND.resolve()
    requested = (root / path).resolve()
    if requested != root and root not in requested.parents:
        return None
    return requested if requested.is_file() else None


@app.get("/pagetrail-icon.png", include_in_schema=False)
@app.get("/favicon.png", include_in_schema=False)
def brand_icon(request: Request) -> FileResponse:
    name = Path(request.url.path).name
    for candidate in (
        FRONTEND / name,
        Path(__file__).parent / "frontend" / "public" / name,
        Path(__file__).parent / "frontend" / name,
        BRAND_ICON,
    ):
        if candidate.is_file():
            return FileResponse(candidate, media_type="image/png")
    raise HTTPException(status_code=404, detail="Icon not found.")


if FRONTEND.exists():
    assets = FRONTEND / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str) -> FileResponse:
        requested = _frontend_file(path)
        if requested is not None:
            return FileResponse(requested)
        return FileResponse(FRONTEND / "index.html")


if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
