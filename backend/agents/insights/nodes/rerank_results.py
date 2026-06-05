"""Node 7: Rerank Results — rerank search results using Voyage AI reranker."""

import json
import time

from backend.services.embedding_service import rerank
from backend.agents.insights.state import InsightsState


async def rerank_results_node(state: InsightsState) -> dict:
    """Rerank search results using Voyage AI's rerank-2.5 model.
    Only runs when there are search results to rerank.
    """
    t0 = time.time()
    search_results = state.get("search_results", [])
    question = state.get("question", "")

    if not search_results:
        prev_queries = state.get("queries_executed", [])
        return {
            "reranked_results": [],
            "queries_executed": prev_queries + [{
                "node": "rerank_results",
                "status": "skipped",
                "duration_ms": round((time.time() - t0) * 1000, 1),
                "reason": "no search results to rerank",
            }],
        }

    try:
        # Build document strings for reranking
        documents = []
        for result in search_results:
            doc_text = (
                f"{result.get('name', '')} | "
                f"{result.get('category', '')}/{result.get('subcategory', '')} | "
                f"Brand: {result.get('brand', '')} | "
                f"Price: RM{result.get('price', {}).get('current_myr', 0):,.2f} | "
                f"Revenue YTD: RM{result.get('performance', {}).get('revenue_ytd', 0):,.2f} | "
                f"Units Sold YTD: {result.get('performance', {}).get('units_sold_ytd', 0):,} | "
                f"Lifecycle: {result.get('lifecycle_stage', '')} | "
                f"Tags: {', '.join(result.get('tags', []))}"
            )
            documents.append(doc_text)

        # Rerank using Voyage AI (synchronous SDK call)
        rerank_results = rerank(
            query=question,
            documents=documents,
            top_k=min(10, len(documents)),
        )

        # Build reranked results list preserving original data
        reranked = []
        for rr in rerank_results:
            idx = rr["index"]
            if idx < len(search_results):
                result = search_results[idx].copy()
                result["rerank_score"] = rr["relevance_score"]
                result["vector_score"] = result.pop("score", 0)
                reranked.append(result)

        prev_queries = state.get("queries_executed", [])
        return {
            "reranked_results": reranked,
            "queries_executed": prev_queries + [{
                "node": "rerank_results",
                "status": "success",
                "duration_ms": round((time.time() - t0) * 1000, 1),
                "rerank_model": "rerank-2.5",
                "input_count": len(search_results),
                "output_count": len(reranked),
                "top_rerank_score": reranked[0]["rerank_score"] if reranked else 0,
            }],
        }

    except Exception as e:
        prev_queries = state.get("queries_executed", [])
        return {
            "reranked_results": search_results,
            "queries_executed": prev_queries + [{
                "node": "rerank_results",
                "status": "error",
                "duration_ms": round((time.time() - t0) * 1000, 1),
                "error": str(e),
                "fallback": "using original search results",
            }],
        }
