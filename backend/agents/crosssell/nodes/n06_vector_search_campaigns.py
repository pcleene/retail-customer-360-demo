"""Node 6: Vector Search Campaigns — semantic campaign matching."""

from backend.agents.crosssell.state import CrossSellState
from backend.agents.crosssell.tracing import traced_node
from backend.database import get_db
from backend.services.embedding_service import embed_for_query


@traced_node("vector_search_campaigns")
async def vector_search_campaigns_node(state: CrossSellState) -> dict:
    queries_executed = list(state.get("queries_executed", []))
    pattern_analysis = state.get("pattern_analysis", "")

    if not pattern_analysis:
        return {"error": "No pattern analysis available for campaign search"}

    db = get_db()
    query_embedding = embed_for_query(pattern_analysis[:2000])

    queries_executed.append({
        "node": "vector_search_campaigns",
        "operation": "embed_for_query",
        "model": "voyage-4-lite",
        "input_length": min(len(pattern_analysis), 2000),
    })

    pipeline = [
        {
            "$vectorSearch": {
                "index": "campaigns_vector",
                "path": "embedding",
                "queryVector": query_embedding,
                "numCandidates": 50,
                "limit": 10,
                "filter": {
                    "status": "active",
                },
            }
        },
        {
            "$project": {
                "_id": 0,
                "embedding": 0,
                "score": {"$meta": "vectorSearchScore"},
            }
        },
    ]

    matched_campaigns = []
    async for doc in await db["campaigns"].aggregate(pipeline):
        matched_campaigns.append(doc)

    queries_executed.append({
        "node": "vector_search_campaigns",
        "collection": "campaigns",
        "operation": "aggregate ($vectorSearch)",
        "index": "campaigns_vector",
        "filter": {"status": "active"},
        "results_count": len(matched_campaigns),
    })

    return {
        "matched_campaigns": matched_campaigns,
        "queries_executed": queries_executed,
    }
