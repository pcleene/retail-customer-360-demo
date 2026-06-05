"""Node 7: Vector Search Content — semantic content matching for campaigns."""

from backend.agents.crosssell.state import CrossSellState
from backend.agents.crosssell.tracing import traced_node
from backend.database import get_db
from backend.services.embedding_service import embed_for_query


@traced_node("vector_search_content")
async def vector_search_content_node(state: CrossSellState) -> dict:
    queries_executed = list(state.get("queries_executed", []))
    matched_campaigns = state.get("matched_campaigns", [])
    pattern_analysis = state.get("pattern_analysis", "")

    if not matched_campaigns:
        return {
            "matched_content": [],
            "queries_executed": queries_executed,
        }

    db = get_db()
    campaign_ids = [c.get("campaign_id") for c in matched_campaigns if c.get("campaign_id")]

    search_text = pattern_analysis[:1000]
    for c in matched_campaigns[:3]:
        search_text += f" {c.get('name', '')} {c.get('description', '')}"

    query_embedding = embed_for_query(search_text[:2000])

    queries_executed.append({
        "node": "vector_search_content",
        "operation": "embed_for_query",
        "model": "voyage-4-lite",
        "input_length": min(len(search_text), 2000),
    })

    pipeline = [
        {
            "$vectorSearch": {
                "index": "content_vector",
                "path": "embedding",
                "queryVector": query_embedding,
                "numCandidates": 50,
                "limit": 10,
                "filter": {
                    "campaign_id": {"$in": campaign_ids},
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

    matched_content = []
    async for doc in await db["content_assets"].aggregate(pipeline):
        matched_content.append(doc)

    queries_executed.append({
        "node": "vector_search_content",
        "collection": "content_assets",
        "operation": "aggregate ($vectorSearch)",
        "index": "content_vector",
        "filter": {"campaign_id": {"$in": campaign_ids}},
        "results_count": len(matched_content),
    })

    return {
        "matched_content": matched_content,
        "queries_executed": queries_executed,
    }
