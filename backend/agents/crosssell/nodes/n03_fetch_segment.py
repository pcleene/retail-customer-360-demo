"""Node 3: Fetch Segment — load representative profiles for a segment."""

from backend.agents.crosssell.state import CrossSellState
from backend.agents.crosssell.tracing import traced_node
from backend.database import get_db


@traced_node("fetch_segment")
async def fetch_segment_node(state: CrossSellState) -> dict:
    db = get_db()
    segment_name = state["customer_id"]
    queries_executed = list(state.get("queries_executed", []))

    segment_pattern = segment_name.replace("_", "[ _]")
    segment_query = {
        "unified_profile.segment": {"$regex": segment_pattern, "$options": "i"}
    }

    pipeline = [
        {"$match": segment_query},
        {"$project": {"_id": 0, "embedding": 0}},
        {"$limit": 20},
    ]

    segment_profiles = []
    async for doc in await db["customers"].aggregate(pipeline):
        segment_profiles.append(doc)

    queries_executed.append({
        "node": "fetch_segment",
        "collection": "customers",
        "operation": "aggregate",
        "pipeline": pipeline,
    })

    if not segment_profiles:
        return {
            "error": f"No customers found for segment '{segment_name}'",
            "segment_query": segment_query,
            "queries_executed": queries_executed,
        }

    return {
        "segment_profiles": segment_profiles,
        "customer_profile": segment_profiles[0],
        "segment_query": segment_query,
        "queries_executed": queries_executed,
    }
