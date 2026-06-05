"""Node 2: Classify Query — LLM determines the query type."""

import json
import time

from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import HumanMessage, SystemMessage

from backend.config import settings
from backend.agents.insights.prompts import CLASSIFY_QUERY_PROMPT
from backend.agents.insights.state import InsightsState


async def classify_query_node(state: InsightsState) -> dict:
    """Use Gemini to classify the question into one of four query types:
    aggregation, search, comparison, or trend.
    """
    t0 = time.time()
    question = state.get("question", "")

    llm = ChatVertexAI(
        model_name=settings.vertex_ai_model,
        project=settings.gcp_project_id,
        location=settings.gcp_location,
        temperature=0.0,
        max_output_tokens=200,
    )

    prompt = CLASSIFY_QUERY_PROMPT.format(question=question)
    messages = [HumanMessage(content=prompt)]

    response = await llm.ainvoke(messages)
    response_text = response.content.strip()

    json_text = response_text
    if "```json" in json_text:
        json_text = json_text.split("```json")[1].split("```")[0]
    elif "```" in json_text:
        json_text = json_text.split("```")[1].split("```")[0]

    try:
        parsed = json.loads(json_text.strip())
        query_type = parsed.get("query_type", "aggregation")
    except (json.JSONDecodeError, ValueError):
        query_type = "aggregation"

    valid_types = {"aggregation", "search", "comparison", "trend"}
    if query_type not in valid_types:
        query_type = "aggregation"

    prev_queries = state.get("queries_executed", [])
    return {
        "query_type": query_type,
        "queries_executed": prev_queries + [{
            "node": "classify_query",
            "status": "success",
            "duration_ms": round((time.time() - t0) * 1000, 1),
            "query_type": query_type,
            "model": settings.vertex_ai_model,
            "llm_response": response_text[:300],
        }],
    }
