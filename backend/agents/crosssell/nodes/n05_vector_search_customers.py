"""Node 5: Vector Search Customers — find similar converted customers."""

from backend.agents.crosssell.state import CrossSellState
from backend.agents.crosssell.tracing import traced_node
from backend.database import get_db
from backend.services.embedding_service import embed_for_query


@traced_node("vector_search_customers")
async def vector_search_customers_node(state: CrossSellState) -> dict:
    queries_executed = list(state.get("queries_executed", []))
    pattern_analysis = state.get("pattern_analysis", "")

    if not pattern_analysis:
        return {"error": "No pattern analysis available for vector search"}

    db = get_db()
    query_embedding = embed_for_query(pattern_analysis[:2000])

    queries_executed.append({
        "node": "vector_search_customers",
        "operation": "embed_for_query",
        "model": "voyage-4-lite",
        "input_length": min(len(pattern_analysis), 2000),
    })

    customer_id = state.get("customer_id", "")

    pipeline = [
        {
            "$vectorSearch": {
                "index": "customers_vector",
                "path": "embedding",
                "queryVector": query_embedding,
                "numCandidates": 150,
                "limit": 20,
            }
        },
        {"$match": {"customer_id": {"$ne": customer_id}}},
        {
            "$project": {
                "_id": 0,
                "embedding": 0,
                "score": {"$meta": "vectorSearchScore"},
            }
        },
        {"$limit": 10},
    ]

    similar_customers = []
    async for doc in await db["customers"].aggregate(pipeline):
        similar_customers.append(doc)

    queries_executed.append({
        "node": "vector_search_customers",
        "collection": "customers",
        "operation": "aggregate ($vectorSearch → $match → $limit)",
        "index": "customers_vector",
        "results_count": len(similar_customers),
    })

    sampled_ids = [c.get("customer_id", "") for c in similar_customers[:5] if c.get("customer_id")]

    return {
        "similar_customers": similar_customers,
        "similar_customers_sampled": sampled_ids,
        "queries_executed": queries_executed,
    }
