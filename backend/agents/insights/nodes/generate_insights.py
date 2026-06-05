"""Node 8: Generate Insights — LLM synthesis of all collected data."""

import json
import time

from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import HumanMessage

from backend.config import settings
from backend.agents.insights.prompts import GENERATE_INSIGHTS_PROMPT
from backend.agents.insights.state import InsightsState


async def generate_insights_node(state: InsightsState) -> dict:
    """Synthesize ALL context — aggregation results, realtime KPIs, anomalies,
    and search results — into comprehensive business insights using Gemini.
    """
    t0 = time.time()
    question = state.get("question", "")
    aggregation_results = state.get("aggregation_results", [])
    realtime_kpis = state.get("realtime_kpis", [])
    has_anomaly = state.get("has_anomaly", False)
    anomaly_message = state.get("anomaly_message", "")
    search_results = state.get("reranked_results", []) or state.get("search_results", [])

    # Format data for the prompt
    agg_text = json.dumps(aggregation_results[:30], indent=2, default=str) if aggregation_results else "No aggregation results available."
    kpi_text = json.dumps(realtime_kpis[:10], indent=2, default=str) if realtime_kpis else "No real-time KPI data available."
    anomaly_context = anomaly_message if has_anomaly else "No anomalies detected in current data."

    search_text = "No semantic search results."
    if search_results:
        # Format search results concisely
        search_items = []
        for r in search_results[:10]:
            item = {
                "product_id": r.get("product_id", ""),
                "name": r.get("name", ""),
                "category": r.get("category", ""),
                "brand": r.get("brand", ""),
                "price_myr": r.get("price", {}).get("current_myr", 0),
                "revenue_ytd": r.get("performance", {}).get("revenue_ytd", 0),
                "units_sold_ytd": r.get("performance", {}).get("units_sold_ytd", 0),
                "lifecycle_stage": r.get("lifecycle_stage", ""),
            }
            if "rerank_score" in r:
                item["relevance_score"] = r["rerank_score"]
            search_items.append(item)
        search_text = json.dumps(search_items, indent=2, default=str)

    llm = ChatVertexAI(
        model_name=settings.vertex_ai_model,
        project=settings.gcp_project_id,
        location=settings.gcp_location,
        temperature=0.3,
        max_output_tokens=3000,
    )

    # Inject user preferences if available from memory recall
    user_preferences = state.get("user_preferences", "")
    pref_block = ""
    if user_preferences:
        pref_block = (
            f"\n\n## User Preferences (apply silently)\n{user_preferences}\n"
        )

    prompt = GENERATE_INSIGHTS_PROMPT.format(
        question=question,
        aggregation_results=agg_text,
        realtime_kpis=kpi_text,
        anomaly_context=anomaly_context,
        search_results=search_text,
    ) + pref_block

    response = await llm.ainvoke([HumanMessage(content=prompt)])

    response_text = response.content.strip()
    prompt_len = len(prompt)

    prev_queries = state.get("queries_executed", [])
    return {
        "insight_analysis": response_text,
        "queries_executed": prev_queries + [{
            "node": "generate_insights",
            "status": "success",
            "duration_ms": round((time.time() - t0) * 1000, 1),
            "model": settings.vertex_ai_model,
            "prompt_chars": prompt_len,
            "response_chars": len(response_text),
            "data_sources": {
                "aggregation_results": len(aggregation_results),
                "realtime_kpis": len(realtime_kpis),
                "search_results": len(search_results),
                "has_anomaly": has_anomaly,
            },
            "preferences_injected": bool(user_preferences),
        }],
    }
