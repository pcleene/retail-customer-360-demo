"""Node 4: Analyze Patterns — LLM analysis of spending, entity gaps, lifecycle."""

import json

from langchain_google_vertexai import ChatVertexAI

from backend.agents.crosssell.prompts import ANALYZE_PATTERNS_PROMPT
from backend.agents.crosssell.state import CrossSellState
from backend.agents.crosssell.tracing import traced_node
from backend.config import settings


@traced_node("analyze_patterns")
async def analyze_patterns_node(state: CrossSellState) -> dict:
    queries_executed = list(state.get("queries_executed", []))
    profile = state.get("customer_profile", {})
    transactions = state.get("transactions", [])

    if not profile:
        return {"error": "No customer profile available for pattern analysis"}

    unified_profile = profile.get("unified_profile", {})
    entity_profiles = profile.get("entity_profiles", {})
    cross_entity_metrics = profile.get("cross_entity_metrics", {})

    unified_str = json.dumps(unified_profile, indent=2, default=str)
    entities_str = json.dumps(entity_profiles, indent=2, default=str)
    metrics_str = json.dumps(cross_entity_metrics, indent=2, default=str)
    txn_str = json.dumps(
        transactions[:30], indent=2, default=str
    ) if transactions else "No transactions available"

    prompt = ANALYZE_PATTERNS_PROMPT.format(
        unified_profile=unified_str,
        entity_profiles=entities_str,
        cross_entity_metrics=metrics_str,
        transactions=txn_str,
    )

    llm = ChatVertexAI(
        model_name=settings.vertex_ai_model,
        project=settings.gcp_project_id,
        location=settings.gcp_location,
        temperature=0.3,
        max_output_tokens=2500,
    )

    response = await llm.ainvoke(prompt)

    queries_executed.append({
        "node": "analyze_patterns",
        "operation": "llm_invoke",
        "model": settings.vertex_ai_model,
        "prompt_length": len(prompt),
        "response_length": len(response.content),
    })

    return {
        "pattern_analysis": response.content,
        "queries_executed": queries_executed,
    }
