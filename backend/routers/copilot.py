"""Co-pilot API endpoints — chat, history, memory, stats, users."""

from fastapi import APIRouter
from pydantic import BaseModel

from backend.agents.copilot.service import copilot_query, get_copilot_stats
from backend.services.memory_service import get_memories
from backend.services.conversation_service import (
    get_history,
    get_conversation,
    resume_conversation,
    list_conversations,
    get_users,
)

router = APIRouter(prefix="/api/copilot", tags=["copilot"])


class CopilotRequest(BaseModel):
    question: str
    session_id: str = "default"
    user_id: str = "anonymous"


@router.post("/ask")
async def ask(req: CopilotRequest):
    try:
        return await copilot_query(req.question, req.session_id, req.user_id)
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Copilot agent error")
        return {
            "question": req.question,
            "answer": f"Sorry, an error occurred: {e}",
            "mql": None,
            "session_id": req.session_id,
            "user_id": req.user_id,
            "latency_ms": 0,
            "memory_trace": [],
        }


@router.get("/history/{session_id}")
async def history(session_id: str):
    return await get_history(session_id)


@router.get("/conversations")
async def conversations(user_id: str | None = None, limit: int = 50):
    return await list_conversations(agent_type="copilot", user_id=user_id, limit=limit)


@router.get("/conversations/{thread_id}")
async def conversation_detail(thread_id: str):
    doc = await get_conversation(thread_id)
    if not doc:
        return {"error": "Conversation not found"}
    return doc


@router.get("/conversations/{thread_id}/resume")
async def conversation_resume(thread_id: str):
    doc = await resume_conversation(thread_id)
    if not doc:
        return {"error": "Conversation not found"}
    return doc


@router.get("/memories/{user_id}")
async def memories(user_id: str):
    return await get_memories(user_id)


@router.get("/stats")
async def stats():
    return get_copilot_stats()


@router.get("/users")
async def users():
    return await get_users()
