"""Node 4: Run Aggregation — execute the MQL pipeline against MongoDB."""

import time

from backend.database import get_db
from backend.agents.insights.state import InsightsState


async def run_aggregation_node(state: InsightsState) -> dict:
    """Execute the MQL aggregation pipeline against the target collection.

    Uses PyMongo AsyncMongoClient: aggregate() needs await (returns async cursor).
    """
    t0 = time.time()
    pipeline = state.get("mql_pipeline", [])
    collection_name = state.get("collection", "products")

    if not pipeline:
        prev_queries = state.get("queries_executed", [])
        return {
            "aggregation_results": [],
            "queries_executed": prev_queries + [{
                "node": "run_aggregation",
                "status": "skipped",
                "duration_ms": round((time.time() - t0) * 1000, 1),
                "reason": "empty pipeline",
            }],
        }

    try:
        db = get_db()
        coll = db[collection_name]

        results = []
        async for doc in await coll.aggregate(pipeline):
            doc.pop("_id", None)
            doc.pop("embedding", None)
            results.append(doc)

        sample = results[:3] if results else []

        prev_queries = state.get("queries_executed", [])
        return {
            "aggregation_results": results[:50],
            "queries_executed": prev_queries + [{
                "node": "run_aggregation",
                "status": "success",
                "duration_ms": round((time.time() - t0) * 1000, 1),
                "collection": collection_name,
                "pipeline_stages": len(pipeline),
                "result_count": len(results),
                "sample_results": sample,
            }],
        }

    except Exception as e:
        prev_queries = state.get("queries_executed", [])
        return {
            "aggregation_results": [],
            "error": f"Aggregation execution failed: {e}",
            "queries_executed": prev_queries + [{
                "node": "run_aggregation",
                "status": "error",
                "duration_ms": round((time.time() - t0) * 1000, 1),
                "collection": collection_name,
                "error": str(e),
            }],
        }
