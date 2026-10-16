import logging
import re
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.api.routes.auth import CurrentUser
from app.core.paths import UPLOAD_DIR
from app.db.session import (
    conversation_belongs_to_user,
    create_update_convo,
    delete_conversation,
    get_chat_history,
    list_conversations,
    save_chat_message,
)
from app.services.agent import get_agent
from app.services.rag import add_document_to_vector_store, retrieve_documents

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

UPLOAD_DIR.mkdir(exist_ok=True)
MAX_UPLOAD_SIZE = 10 * 1024 * 1024


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
    cleaned = re.sub(
        r"<think(?:ing)?>[\s\S]*?</think(?:ing)?>", "", cleaned, flags=re.I
    )
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


def build_checkpoint_thread_id(user_id: int, conversation_thread_id: str) -> str:
    return f"user:{user_id}:conversation:{conversation_thread_id}"


def last_assistant_text(messages: list[Any]) -> str:
    for message in reversed(messages):
        if getattr(message, "type", None) == "tool":
            continue
        text = clean_llm_output(message_content(message))
        if text:
            return text
    return "I was unable to produce a response. Please try again."


@router.get("/api/conversations")
def conversations(current_user: CurrentUser) -> list[dict[str, str]]:
    return [
        {
            "thread_id": conversation.thread_id,
            "name": conversation.name,
            "updated_at": conversation.updated_at,
        }
        for conversation in list_conversations(current_user.id)
    ]


@router.post("/api/conversations")
def new_conversation(current_user: CurrentUser) -> dict[str, str]:
    thread_id = str(uuid.uuid4())
    create_update_convo(thread_id, current_user.id, "", "New conversation")
    return {"thread_id": thread_id, "name": "New conversation"}


@router.get("/api/conversations/{thread_id}/messages")
def history(thread_id: str, current_user: CurrentUser) -> list[dict[str, str]]:
    return [
        {"role": message.role, "content": message.content}
        for message in get_chat_history(thread_id, current_user.id)
    ]


@router.delete("/api/conversations/{thread_id}")
def remove_conversation(thread_id: str, current_user: CurrentUser) -> dict[str, bool]:
    if not delete_conversation(thread_id, current_user.id):
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return {"deleted": True}


@router.post("/api/chat")
def chat(request: ChatRequest, current_user: CurrentUser) -> dict[str, str]:
    if not create_update_convo(
        request.thread_id, current_user.id, request.message, request.message[:48]
    ):
        raise HTTPException(status_code=404, detail="Conversation not found.")

    save_chat_message(request.thread_id, current_user.id, "user", request.message)

    try:
        document_context = retrieve_documents(
            request.message, request.thread_id, current_user.id, k=5
        )
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

        checkpoint_thread_id = build_checkpoint_thread_id(
            current_user.id,
            request.thread_id,
        )

        result = agent.invoke(
            {"messages": [{"role": "user", "content": prompt}]},
            config={
                "configurable": {
                    "thread_id": checkpoint_thread_id,
                    "conversation_thread_id": request.thread_id,
                    "user_id": current_user.id,
                }
            },
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


@router.post("/api/conversations/{thread_id}/files")
async def upload_file(
    thread_id: str, current_user: CurrentUser, file: UploadFile = File(...)
) -> dict[str, Any]:
    if not conversation_belongs_to_user(thread_id, current_user.id):
        raise HTTPException(status_code=404, detail="Conversation not found.")

    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".pdf", ".docx", ".txt", ".md"}:
        raise HTTPException(
            status_code=400, detail="Upload a PDF, DOCX, TXT, or MD file."
        )

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
