"""Node 6: Vector Search Products — semantic search for search/comparison query types."""

import time

from backend.database import get_db
from backend.services.embedding_service import embed_for_query
from backend.agents.insights.state import InsightsState


async def vector_search_products_node(state: InsightsState) -> dict:
    """Run $vectorSearch on the products collection for search and comparison query types.
    Skips for aggregation and trend types where MQL pipelines handle data retrieval.

    Uses voyage-4-lite for query embedding (shared 1024d space with voyage-4-large index).
    Uses PyMongo AsyncMongoClient: aggregate() needs await.
    """
    t0 = time.time()
    query_type = state.get("query_type", "aggregation")
    question = state.get("question", "")
    rbac_filter = state.get("rbac_filter", {})

    if query_type not in ("search", "comparison"):
        prev_queries = state.get("queries_executed", [])
        return {
            "search_results": [],
            "queries_executed": prev_queries + [{
                "node": "vector_search_products",
                "status": "skipped",
                "duration_ms": round((time.time() - t0) * 1000, 1),
                "reason": f"query_type={query_type} does not require vector search",
            }],
        }

    try:
        # Generate query embedding using voyage-4-lite
        query_embedding = embed_for_query(question)

        # Build the $vectorSearch pipeline
        vector_search_stage = {
            "$vectorSearch": {
                "index": "products_vector",
                "path": "embedding",
                "queryVector": query_embedding,
                "numCandidates": 100,
                "limit": 20,
            }
        }

        # Apply RBAC filter within vector search if present
        if rbac_filter:
            vector_search_stage["$vectorSearch"]["filter"] = rbac_filter

        pipeline = [
            vector_search_stage,
            {
                "$project": {
                    "_id": 0,
                    "product_id": 1,
                    "name": 1,
                    "category": 1,
                    "subcategory": 1,
                    "brand": 1,
                    "supplier_id": 1,
                    "entity": 1,
                    "price.current_myr": 1,
                    "price.msrp_myr": 1,
                    "inventory": 1,
                    "performance.revenue_ytd": 1,
                    "performance.units_sold_ytd": 1,
                    "lifecycle_stage": 1,
                    "tags": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]

        db = get_db()
        coll = db["products"]

        results = []
        async for doc in await coll.aggregate(pipeline):
            results.append(doc)

        prev_queries = state.get("queries_executed", [])
        return {
            "search_results": results,
            "queries_executed": prev_queries + [{
                "node": "vector_search_products",
                "status": "success",
                "duration_ms": round((time.time() - t0) * 1000, 1),
                "collection": "products",
                "index": "products_vector",
                "embedding_model": "voyage-4-lite",
                "result_count": len(results),
                "has_rbac_filter": bool(rbac_filter),
                "mql_pipeline": pipeline,
                "top_score": results[0].get("score", 0) if results else 0,
            }],
        }

    except Exception as e:
        prev_queries = state.get("queries_executed", [])
        return {
            "search_results": [],
            "queries_executed": prev_queries + [{
                "node": "vector_search_products",
                "status": "error",
                "duration_ms": round((time.time() - t0) * 1000, 1),
                "error": str(e),
            }],
        }
