"""Product Insights API endpoints — chat, history, memory, stats."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.auth.middleware import get_current_user
from backend.agents.insights.service import insights_query, get_insights_stats
from backend.services.memory_service import get_memories
from backend.services.conversation_service import (
    get_history,
    get_conversation,
    resume_conversation,
    list_conversations,
    get_users,
)

router = APIRouter(prefix="/api/insights", tags=["insights"])


class InsightsRequest(BaseModel):
    question: str
    role: str = "internal_staff"
    session_id: str = "default"
    user_id: str = "anonymous"


@router.post("/ask")
async def ask_insights(
    req: InsightsRequest,
    user: dict = Depends(get_current_user),
):
    """Run the 9-node product insights agent pipeline with RBAC + memory."""
    role = user.get("role", req.role)
    supplier_id = user.get("supplier_id", "")
    user_id = req.user_id if req.user_id != "anonymous" else user.get("user_id", "anonymous")

    try:
        return await insights_query(
            question=req.question,
            role=role,
            supplier_id=supplier_id or "",
            session_id=req.session_id,
            user_id=user_id,
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Insights agent error")
        return {
            "question": req.question,
            "insight": f"Sorry, an error occurred: {e}",
            "error": str(e),
            "role": role,
            "query_type": "",
            "mql": [],
            "aggregation_results": [],
            "search_results": [],
            "has_anomaly": False,
            "anomaly_message": "",
            "queries_executed": [],
            "session_id": req.session_id,
            "user_id": user_id,
            "latency_ms": 0,
            "preferences_applied": False,
            "preference_saved": False,
        }


@router.get("/history/{session_id}")
async def history(session_id: str):
    return await get_history(session_id)


@router.get("/conversations")
async def conversations(user_id: str | None = None, limit: int = 50):
    return await list_conversations(agent_type="insights", user_id=user_id, limit=limit)


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
    return get_insights_stats()


@router.get("/users")
async def users():
    return await get_users()
