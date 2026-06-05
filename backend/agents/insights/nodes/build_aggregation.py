"""Node 3: Build Aggregation — LLM generates MQL pipeline with RBAC injection."""

import json
import time

from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import HumanMessage

from backend.config import settings
from backend.agents.insights.prompts import BUILD_AGGREGATION_PROMPT
from backend.agents.insights.state import InsightsState


async def build_aggregation_node(state: InsightsState) -> dict:
    """Use Gemini to generate a MongoDB aggregation pipeline for the question.
    Injects RBAC filter as the FIRST $match stage.
    """
    t0 = time.time()
    question = state.get("question", "")
    rbac_filter = state.get("rbac_filter", {})
    query_type = state.get("query_type", "aggregation")

    if rbac_filter:
        rbac_context = (
            f"MANDATORY: Insert this as the FIRST $match stage in the pipeline: "
            f'{json.dumps(rbac_filter)}\n'
            f"This user can ONLY see data matching this filter."
        )
    else:
        rbac_context = "No RBAC filter needed — this is an internal staff user with full access."

    llm = ChatVertexAI(
        model_name=settings.vertex_ai_model,
        project=settings.gcp_project_id,
        location=settings.gcp_location,
        temperature=0.1,
        max_output_tokens=3000,
    )

    prompt = BUILD_AGGREGATION_PROMPT.format(
        question=question,
        rbac_context=rbac_context,
    )
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
        collection = parsed.get("collection", "products")
        pipeline = parsed.get("pipeline", [])

        if rbac_filter:
            if pipeline and "$match" in pipeline[0]:
                pipeline[0]["$match"].update(rbac_filter)
            else:
                pipeline.insert(0, {"$match": rbac_filter})

        stage_types = [list(s.keys())[0] for s in pipeline if isinstance(s, dict)]

        prev_queries = state.get("queries_executed", [])
        return {
            "mql_pipeline": pipeline,
            "collection": collection,
            "queries_executed": prev_queries + [{
                "node": "build_aggregation",
                "status": "success",
                "duration_ms": round((time.time() - t0) * 1000, 1),
                "model": settings.vertex_ai_model,
                "collection": collection,
                "pipeline_stages": len(pipeline),
                "stage_types": stage_types,
                "mql_pipeline": pipeline,
                "explanation": parsed.get("explanation", ""),
                "rbac_injected": bool(rbac_filter),
            }],
        }

    except (json.JSONDecodeError, ValueError) as e:
        prev_queries = state.get("queries_executed", [])
        return {
            "mql_pipeline": [],
            "collection": "products",
            "error": f"Failed to parse MQL pipeline: {e}",
            "queries_executed": prev_queries + [{
                "node": "build_aggregation",
                "status": "error",
                "duration_ms": round((time.time() - t0) * 1000, 1),
                "error": str(e),
            }],
        }
