"""Product Insights service — memory-aware wrapper around the 9-node pipeline.

Handles:
- Recalling user preferences before the pipeline runs
- Saving preferences when the user asks to remember something
- Conversation persistence
- Stats tracking
"""

import asyncio
import logging
import time

from backend.agents.insights.graph import build_insights_graph
from backend.services.memory_service import get_memory_store
from backend.services.conversation_service import save_conversation_turn

logger = logging.getLogger(__name__)

_stats = {"totalQueries": 0, "totalLatencyMs": 0.0}


def get_insights_stats() -> dict:
    total = _stats["totalQueries"]
    return {
        "totalQueries": total,
        "activeSessions": 0,
        "avgLatencyMs": round(_stats["totalLatencyMs"] / total, 0) if total > 0 else 0,
    }


async def _recall_user_preferences(user_id: str) -> str:
    """Check the memory store for user preferences before running the pipeline."""
    store = get_memory_store()
    if not store or user_id in ("anonymous", ""):
        return ""
    try:
        namespace = ("user", user_id, "preferences")
        items = await store.asearch(
            namespace, query="user preferences formatting display style", limit=5
        )
        if not items:
            return ""
        lines = []
        for item in items:
            lines.append(f"- {item.key}: {item.value.get('content', str(item.value))}")
        return "\n".join(lines)
    except Exception as e:
        logger.debug("Could not recall preferences for %s: %s", user_id, e)
        return ""


async def _save_preference_if_requested(user_id: str, question: str) -> bool:
    """Detect 'remember' / 'preference' language and save to memory store."""
    store = get_memory_store()
    if not store or user_id in ("anonymous", ""):
        return False

    triggers = ["remember", "always", "my preference", "note that", "from now on"]
    q_lower = question.lower()
    if not any(t in q_lower for t in triggers):
        return False

    try:
        namespace = ("user", user_id, "preferences")
        key = "insights_preference_" + str(int(time.time()))
        await store.aput(namespace, key, {"content": question})
        logger.info("Saved insights preference for user %s: %s", user_id, key)
        return True
    except Exception as e:
        logger.warning("Failed to save preference for %s: %s", user_id, e)
        return False


async def insights_query(
    question: str,
    role: str = "internal_staff",
    supplier_id: str = "",
    session_id: str = "default",
    user_id: str = "anonymous",
) -> dict:
    """Run the 9-node insights pipeline with memory-aware context."""
    start = time.time()

    saved_pref = await _save_preference_if_requested(user_id, question)

    user_preferences = await _recall_user_preferences(user_id)

    agent = build_insights_graph()
    initial_state = {
        "question": question,
        "role": role,
        "supplier_id": supplier_id or "",
        "user_id": user_id,
        "session_id": session_id,
        "user_preferences": user_preferences,
    }

    result = await agent.ainvoke(initial_state)

    latency_ms = round((time.time() - start) * 1000, 0)

    _stats["totalQueries"] += 1
    _stats["totalLatencyMs"] += latency_ms

    insight_text = result.get("formatted_response", result.get("insight_analysis", ""))
    mql_pipeline = result.get("mql_pipeline", [])

    asyncio.create_task(
        save_conversation_turn(
            "insights", session_id, user_id, question, insight_text, mql_pipeline, latency_ms
        )
    )

    response = {
        "question": question,
        "role": role,
        "query_type": result.get("query_type", ""),
        "mql": mql_pipeline,
        "aggregation_results": result.get("aggregation_results", [])[:20],
        "search_results": result.get("reranked_results", result.get("search_results", []))[:10],
        "has_anomaly": result.get("has_anomaly", False),
        "anomaly_message": result.get("anomaly_message", ""),
        "insight": insight_text,
        "queries_executed": result.get("queries_executed", []),
        "error": result.get("error", ""),
        "session_id": session_id,
        "user_id": user_id,
        "latency_ms": latency_ms,
        "preferences_applied": bool(user_preferences),
        "preference_saved": saved_pref,
    }
    return response
