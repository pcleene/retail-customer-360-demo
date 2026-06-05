"""Node 8: Analyze Similar Conversions — LLM analysis of lookalike conversion patterns."""

import json
import re

from langchain_google_vertexai import ChatVertexAI

from backend.agents.crosssell.prompts import ANALYZE_SIMILAR_CONVERSIONS_PROMPT
from backend.agents.crosssell.state import CrossSellState
from backend.agents.crosssell.tracing import traced_node
from backend.config import settings


@traced_node("analyze_similar_conversions")
async def analyze_similar_conversions_node(state: CrossSellState) -> dict:
    queries_executed = list(state.get("queries_executed", []))
    similar_customers = state.get("similar_customers", [])
    pattern_analysis = state.get("pattern_analysis", "")

    if not similar_customers:
        return {
            "similar_conversion_analysis": "No similar converted customers found. "
            "Recommendations will be based on pattern analysis alone.",
            "similar_conversion_rate": 0.0,
            "queries_executed": queries_executed,
        }

    lookalike_summaries = []
    for cust in similar_customers[:8]:
        summary = {
            "customer_id": cust.get("customer_id", ""),
            "segment": cust.get("segment", ""),
            "tier": cust.get("tier", ""),
            "entities": cust.get("entities", []),
            "ltv_myr": cust.get("cross_entity_metrics", {}).get("total_ltv", 0),
            "active_campaigns": cust.get("active_campaigns", []),
            "cross_entity_metrics": cust.get("cross_entity_metrics", {}),
            "channel_engagement_rates": cust.get(
                "interaction_history", {}
            ).get("channel_engagement_rates", {}),
            "vector_score": cust.get("score", 0),
        }
        lookalike_summaries.append(summary)

    similar_str = json.dumps(lookalike_summaries, indent=2, default=str)

    prompt = ANALYZE_SIMILAR_CONVERSIONS_PROMPT.format(
        pattern_analysis=pattern_analysis[:1500],
        similar_customers=similar_str,
    )

    llm = ChatVertexAI(
        model_name=settings.vertex_ai_model,
        project=settings.gcp_project_id,
        location=settings.gcp_location,
        temperature=0.3,
        max_output_tokens=2000,
    )

    response = await llm.ainvoke(prompt)

    queries_executed.append({
        "node": "analyze_similar_conversions",
        "operation": "llm_invoke",
        "model": settings.vertex_ai_model,
        "lookalikes_analyzed": len(lookalike_summaries),
        "prompt_length": len(prompt),
        "response_length": len(response.content),
    })

    conversion_rate = _extract_conversion_rate(response.content, similar_customers)

    return {
        "similar_conversion_analysis": response.content,
        "similar_conversion_rate": conversion_rate,
        "queries_executed": queries_executed,
    }


def _extract_conversion_rate(llm_text: str, similar_customers: list[dict]) -> float:
    """Try to extract a conversion probability from the LLM output,
    falling back to a heuristic based on actual campaign statuses."""
    match = re.search(r"(\d{1,3})%", llm_text)
    if match:
        return min(float(match.group(1)) / 100.0, 1.0)

    converted = sum(
        1 for c in similar_customers
        if any(
            ac.get("status") == "converted"
            for ac in c.get("active_campaigns", [])
        )
    )
    if similar_customers:
        return round(converted / len(similar_customers), 2)
    return 0.0
