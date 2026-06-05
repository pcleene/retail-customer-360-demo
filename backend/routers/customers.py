"""Customer API endpoints."""

import logging
import traceback

from fastapi import APIRouter, HTTPException

from backend.models.search import SearchFilters
from backend.services.customer_service import (
    search_customers_hybrid,
    get_customer_by_id,
    get_customer_transactions,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.post("/search")
async def search_customers(filters: SearchFilters):
    return await search_customers_hybrid(filters)


@router.get("/{customer_id}")
async def get_customer(customer_id: str):
    customer = await get_customer_by_id(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.get("/{customer_id}/transactions")
async def get_transactions(customer_id: str, limit: int = 50):
    return await get_customer_transactions(customer_id, limit=limit)


@router.post("/{customer_id}/recommend")
async def generate_recommendation(customer_id: str):
    """Run the cross-sell agent pipeline for a single customer."""
    try:
        from backend.agents.crosssell.graph import crosssell_agent

        result = await crosssell_agent.ainvoke({"customer_id": customer_id})

        if result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])

        structured = result.get("structured_recommendation", {})

        return {
            "customer_id": customer_id,
            "mode": result.get("mode", "individual"),
            "pattern_analysis": result.get("pattern_analysis", ""),
            "similar_customers": [
                {
                    "customer_id": c.get("customer_id"),
                    "name": c.get("unified_profile", {}).get("name", ""),
                    "score": c.get("score", 0),
                }
                for c in result.get("similar_customers", [])[:5]
            ],
            "matched_campaigns": [
                {
                    "campaign_id": c.get("campaign_id"),
                    "name": c.get("name"),
                    "score": c.get("score", 0),
                    "rerank_score": c.get("rerank_score", 0),
                }
                for c in result.get("reranked_campaigns", result.get("matched_campaigns", []))
            ],
            "matched_content": [
                {
                    "content_id": c.get("content_id"),
                    "headline": c.get("headline", ""),
                    "channel": c.get("channel", ""),
                    "rerank_score": c.get("rerank_score", 0),
                }
                for c in result.get("reranked_content", result.get("matched_content", []))
            ],
            "recommended_channel": result.get("optimal_channel", ""),
            "recommendation": structured.get("reasoning", result.get("recommendation", "")),
            "structured_recommendation": structured,
            "reasoning_steps": result.get("reasoning_steps", []),
            "enrollment_result": result.get("enrollment_result", {}),
            "queries_executed": result.get("queries_executed", []),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Cross-sell agent failed for %s", customer_id)
        raise HTTPException(status_code=500, detail=f"Agent pipeline failed: {str(e)}")
