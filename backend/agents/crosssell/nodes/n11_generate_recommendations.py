"""Node 11: Generate Recommendations — structured JSON from Gemini."""

import json
import logging
import re

from langchain_google_vertexai import ChatVertexAI

from backend.agents.crosssell.prompts import GENERATE_RECOMMENDATIONS_PROMPT
from backend.agents.crosssell.state import CrossSellState
from backend.agents.crosssell.tracing import traced_node
from backend.config import settings

logger = logging.getLogger(__name__)


@traced_node("generate_recommendations")
async def generate_recommendations_node(state: CrossSellState) -> dict:
    queries_executed = list(state.get("queries_executed", []))
    profile = state.get("customer_profile", {})

    unified = profile.get("unified_profile", {})
    customer_summary = json.dumps({
        "customer_id": profile.get("customer_id", ""),
        "name": unified.get("name", ""),
        "tier": profile.get("tier", unified.get("tier", "")),
        "segment": profile.get("segment", unified.get("segment", "")),
        "entities": profile.get("entities", []),
        "ltv_myr": profile.get("cross_entity_metrics", {}).get("total_ltv", 0),
        "cross_sell_score": profile.get("cross_entity_metrics", {}).get("cross_sell_score", 0),
        "churn_risk": profile.get("cross_entity_metrics", {}).get("churn_risk", 0),
        "state": unified.get("address", {}).get("state", ""),
        "city": unified.get("address", {}).get("city", ""),
        "entity_profiles_summary": {
            "RetailGroup_co": bool(profile.get("entity_profiles", {}).get("RetailGroup_co")),
            "RetailGroup_credit": bool(profile.get("entity_profiles", {}).get("RetailGroup_credit")),
            "RetailGroup_bank": bool(profile.get("entity_profiles", {}).get("RetailGroup_bank")),
        },
    }, indent=2, default=str)

    reranked_campaigns = state.get("reranked_campaigns", [])
    campaigns_str = json.dumps([
        {
            "campaign_id": c.get("campaign_id", ""),
            "name": c.get("name", ""),
            "entity": c.get("entity", ""),
            "type": c.get("type", ""),
            "description": c.get("description", ""),
            "rerank_score": round(c.get("rerank_score", c.get("score", 0)), 4),
        }
        for c in reranked_campaigns[:5]
    ], indent=2, default=str)

    reranked_content = state.get("reranked_content", [])
    content_str = json.dumps([
        {
            "content_id": c.get("content_id", ""),
            "headline": c.get("headline", ""),
            "channel": c.get("channel", ""),
            "target_persona": c.get("target_persona", ""),
            "rerank_score": round(c.get("rerank_score", c.get("score", 0)), 4),
        }
        for c in reranked_content[:5]
    ], indent=2, default=str)

    prompt = GENERATE_RECOMMENDATIONS_PROMPT.format(
        customer_summary=customer_summary,
        pattern_analysis=state.get("pattern_analysis", "N/A")[:2000],
        similar_conversion_analysis=state.get("similar_conversion_analysis", "N/A")[:1500],
        optimal_channel=state.get("optimal_channel", "email"),
        channel_reasoning=state.get("channel_reasoning", "N/A"),
        reranked_campaigns=campaigns_str,
        reranked_content=content_str,
    )

    llm = ChatVertexAI(
        model_name=settings.vertex_ai_model,
        project=settings.gcp_project_id,
        location=settings.gcp_location,
        temperature=0.3,
        max_output_tokens=3000,
    )

    response = await llm.ainvoke(prompt)

    queries_executed.append({
        "node": "generate_recommendations",
        "operation": "llm_invoke",
        "model": settings.vertex_ai_model,
        "prompt_length": len(prompt),
        "response_length": len(response.content),
    })

    structured = _parse_structured_output(
        response.content, reranked_campaigns, reranked_content, state
    )

    return {
        "recommendation": structured.get("reasoning", response.content),
        "structured_recommendation": structured,
        "expected_ltv_uplift": structured.get("expected_ltv_uplift", 0),
        "queries_executed": queries_executed,
    }


def _parse_structured_output(
    raw: str,
    campaigns: list[dict],
    content: list[dict],
    state: dict,
) -> dict:
    """Parse the LLM JSON output, falling back to sensible defaults."""
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return _validate_and_enrich(parsed, campaigns, content, state)
    except json.JSONDecodeError:
        logger.warning("Failed to parse structured recommendation JSON, building from context")

    return _build_fallback(raw, campaigns, content, state)


def _validate_and_enrich(
    parsed: dict,
    campaigns: list[dict],
    content: list[dict],
    state: dict,
) -> dict:
    """Ensure all required fields exist with correct types."""
    top_campaign = campaigns[0] if campaigns else {}
    top_content = content[0] if content else {}

    return {
        "primary_campaign_id": parsed.get("primary_campaign_id", top_campaign.get("campaign_id", "")),
        "primary_campaign_name": parsed.get("primary_campaign_name", top_campaign.get("name", "")),
        "content_asset_id": parsed.get("content_asset_id", top_content.get("content_id")),
        "content_headline": parsed.get("content_headline", top_content.get("headline")),
        "recommended_channel": parsed.get("recommended_channel", state.get("optimal_channel", "email")),
        "reasoning": parsed.get("reasoning", ""),
        "expected_ltv_uplift": float(parsed.get("expected_ltv_uplift", 0)),
        "conversion_probability": float(parsed.get("conversion_probability", 0)),
        "risk_factors": parsed.get("risk_factors", []),
        "fallback_campaign_id": parsed.get("fallback_campaign_id"),
        "personalization_notes": parsed.get("personalization_notes", ""),
    }


def _build_fallback(
    raw_text: str,
    campaigns: list[dict],
    content: list[dict],
    state: dict,
) -> dict:
    """Build a structured dict from the raw text + upstream context."""
    top_campaign = campaigns[0] if campaigns else {}
    top_content = content[0] if content else {}

    return {
        "primary_campaign_id": top_campaign.get("campaign_id", ""),
        "primary_campaign_name": top_campaign.get("name", ""),
        "content_asset_id": top_content.get("content_id"),
        "content_headline": top_content.get("headline"),
        "recommended_channel": state.get("optimal_channel", "email"),
        "reasoning": raw_text[:500],
        "expected_ltv_uplift": 0,
        "conversion_probability": state.get("similar_conversion_rate", 0),
        "risk_factors": [],
        "fallback_campaign_id": campaigns[1].get("campaign_id") if len(campaigns) > 1 else None,
        "personalization_notes": "",
    }
