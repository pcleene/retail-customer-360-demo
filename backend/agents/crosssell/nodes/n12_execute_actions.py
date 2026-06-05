"""Node 12: Execute Actions — enroll customer in campaign + create action record.

Writes documents that conform to the canonical ActiveCampaign and CampaignAction
Pydantic models defined in backend/models/.
"""

import uuid
from datetime import datetime, timezone

from backend.agents.crosssell.state import CrossSellState
from backend.agents.crosssell.tracing import traced_node
from backend.database import get_db


@traced_node("execute_actions")
async def execute_actions_node(state: CrossSellState) -> dict:
    queries_executed = list(state.get("queries_executed", []))
    profile = state.get("customer_profile", {})
    reranked_campaigns = state.get("reranked_campaigns", [])
    reranked_content = state.get("reranked_content", [])
    structured = state.get("structured_recommendation", {})

    if not reranked_campaigns:
        return {
            "enrollment_result": {"status": "skipped", "reason": "No campaigns to enroll"},
            "enrolled": False,
            "queries_executed": queries_executed,
        }

    db = get_db()
    customer_id = state["customer_id"]
    now = datetime.now(timezone.utc)
    enrollment_id = f"ENR-{uuid.uuid4().hex[:12].upper()}"
    action_id = f"ACT-{uuid.uuid4().hex[:12].upper()}"

    top_campaign = reranked_campaigns[0]
    top_content = reranked_content[0] if reranked_content else {}

    campaign_id = structured.get("primary_campaign_id") or top_campaign.get("campaign_id", "")
    campaign_name = structured.get("primary_campaign_name") or top_campaign.get("name", "")
    content_id = structured.get("content_asset_id") or top_content.get("content_id")
    content_headline = structured.get("content_headline") or top_content.get("headline")
    recommended_channel = structured.get("recommended_channel") or state.get("optimal_channel", "email")
    reasoning = structured.get("reasoning", state.get("recommendation", ""))
    expected_ltv_uplift = state.get("expected_ltv_uplift", 0)
    similar_conversion_rate = state.get("similar_conversion_rate", 0)
    similar_customers_sampled = state.get("similar_customers_sampled", [])

    active_campaign_doc = {
        "campaign_id": campaign_id,
        "campaign_name": campaign_name,
        "enrollment_id": enrollment_id,
        "enrolled_date": now.isoformat(),
        "enrolled_by": "agent",
        "signal_id": None,
        "content_asset_id": content_id,
        "content_headline": content_headline,
        "recommended_channel": recommended_channel,
        "reasoning": reasoning[:500],
        "similar_customer_conversion_rate": similar_conversion_rate,
        "expected_ltv_uplift": expected_ltv_uplift,
        "similar_customers_sampled": similar_customers_sampled,
        "status": "enrolled",
        "converted_at": None,
        "revenue_realized_myr": 0.0,
    }

    update_result = await db["customers"].update_one(
        {"customer_id": customer_id},
        {"$push": {"active_campaigns": active_campaign_doc}},
    )

    queries_executed.append({
        "node": "execute_actions",
        "collection": "customers",
        "operation": "update_one ($push active_campaigns)",
        "customer_id": customer_id,
        "matched": update_result.matched_count,
        "modified": update_result.modified_count,
    })

    reasoning_steps_raw = state.get("reasoning_steps", [])
    reasoning_steps_docs = [
        {
            "node": step.get("step", ""),
            "started_at": "",
            "finished_at": "",
            "summary": step.get("detail", "")[:500] if step.get("detail") else "",
            "details": {"status": step.get("status", "ok"), "duration_ms": step.get("duration_ms", 0)},
        }
        for step in reasoning_steps_raw
    ]

    campaign_action_doc = {
        "action_id": action_id,
        "enrollment_id": enrollment_id,
        "customer_id": customer_id,
        "customer_name_snapshot": profile.get("unified_profile", {}).get("name", ""),
        "campaign_id": campaign_id,
        "campaign_name_snapshot": campaign_name,
        "content_id": content_id,
        "recommended_channel": recommended_channel,
        "triggered_by": "agent",
        "signal_id": None,
        "agent_thread_id": f"thread-{uuid.uuid4().hex[:8]}",
        "reasoning": reasoning[:1000],
        "reasoning_steps": reasoning_steps_docs,
        "similar_customers_sampled": similar_customers_sampled,
        "similar_conversion_rate": similar_conversion_rate,
        "expected_ltv_uplift": expected_ltv_uplift,
        "targeting_match_score": state.get("targeting_match_score", 0),
        "semantic_similarity": state.get("semantic_similarity", 0),
        "rerank_score": top_campaign.get("rerank_score", 0),
        "status": "enrolled",
        "created_at": now.isoformat(),
        "last_updated_at": now.isoformat(),
        "converted_at": None,
        "revenue_realized_myr": 0.0,
    }

    insert_result = await db["campaign_actions"].insert_one(campaign_action_doc)

    queries_executed.append({
        "node": "execute_actions",
        "collection": "campaign_actions",
        "operation": "insert_one",
        "inserted_id": str(insert_result.inserted_id),
    })

    enrollment_result = {
        "status": "enrolled",
        "enrolled": True,
        "customer_id": customer_id,
        "enrollment_id": enrollment_id,
        "action_id": action_id,
        "campaign_id": campaign_id,
        "campaign_name": campaign_name,
        "channel": recommended_channel,
        "content_id": content_id,
        "content_headline": content_headline,
        "expected_ltv_uplift": expected_ltv_uplift,
        "similar_conversion_rate": similar_conversion_rate,
        "enrolled_at": now.isoformat(),
    }

    return {
        "enrollment_result": enrollment_result,
        "enrolled": True,
        "queries_executed": queries_executed,
    }
