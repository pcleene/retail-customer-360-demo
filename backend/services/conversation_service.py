"""Conversation persistence, metadata generation, history retrieval, demo users.

Shared service used by both the Copilot and Product Insights chatbots.
Follows the FuelRetail analytics pattern: save turns → async metadata classification
→ search embeddings → conversation resume via LangGraph checkpoint.
"""

import asyncio
import json
import re
import uuid
import logging
from datetime import datetime, timezone

from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import HumanMessage

from backend.config import settings
from backend.database import get_db
from backend.services.memory_service import VoyageEmbeddings, get_checkpointer

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Conversation Turn Persistence
# ---------------------------------------------------------------------------

async def save_conversation_turn(
    agent_type: str,
    session_id: str,
    user_id: str,
    question: str,
    answer: str,
    mql: str | dict | None,
    latency_ms: float,
):
    """Save or append a conversation turn to chat_conversations.

    agent_type: "copilot" or "insights" — stored for filtering.
    """
    try:
        db = get_db()
        coll = db["chat_conversations"]
        now = datetime.now(timezone.utc)

        message_pair = {
            "id": str(uuid.uuid4()),
            "question": question,
            "content": answer,
            "mql": mql or "",
            "latency_ms": latency_ms,
            "timestamp": now.isoformat(),
        }

        existing = await coll.find_one({"threadId": session_id})

        if existing is None:
            doc = {
                "threadId": session_id,
                "userId": user_id,
                "agentType": agent_type,
                "messages": [message_pair],
                "turnCount": 1,
                "lastQuestion": question,
                "createdAt": now,
                "updatedAt": now,
                "title": "",
                "summary": "",
                "category": "",
                "topics": [],
                "entities": [],
                "queryTypes": [],
                "complexity": "",
                "intent": "",
                "collections": [],
            }
            await coll.insert_one(doc)
            asyncio.create_task(_generate_conversation_metadata(session_id, agent_type))
        else:
            turn_count = existing.get("turnCount", 0) + 1
            await coll.update_one(
                {"threadId": session_id},
                {
                    "$push": {"messages": message_pair},
                    "$set": {
                        "turnCount": turn_count,
                        "lastQuestion": question,
                        "updatedAt": now,
                    },
                },
            )
            if turn_count % 3 == 0:
                asyncio.create_task(_generate_conversation_metadata(session_id, agent_type))

    except Exception as e:
        logger.error("Failed to save conversation turn: %s", e)


# ---------------------------------------------------------------------------
# Conversation Metadata (auto-classification via LLM)
# ---------------------------------------------------------------------------

_COPILOT_CATEGORIES = "customer-360, cross-sell, churn-risk, campaign, loyalty, entity-analysis, support, system"
_INSIGHTS_CATEGORIES = "product-performance, category-analysis, supplier-metrics, pricing, inventory, trend-analysis, anomaly, system"


async def _generate_conversation_metadata(session_id: str, agent_type: str):
    """Use Gemini to classify and tag a conversation for faceted search."""
    try:
        db = get_db()
        coll = db["chat_conversations"]
        doc = await coll.find_one({"threadId": session_id})
        if not doc:
            return

        digest_parts = []
        for msg in doc.get("messages", [])[:20]:
            digest_parts.append(f"Q: {msg['question']}")
            ans = msg.get("content", "")[:500]
            digest_parts.append(f"A: {ans}")
        digest = "\n".join(digest_parts)

        categories = _COPILOT_CATEGORIES if agent_type == "copilot" else _INSIGHTS_CATEGORIES

        model = ChatVertexAI(
            model_name=settings.vertex_ai_model,
            project=settings.gcp_project_id,
            location=settings.gcp_location,
            temperature=0.1,
            max_output_tokens=500,
        )

        classification_prompt = (
            f"Classify this Retail Customer 360 {agent_type} chatbot conversation. "
            f"Return ONLY valid JSON with these fields:\n"
            f"- title: short descriptive title (max 60 chars)\n"
            f"- summary: 1-2 sentence summary\n"
            f"- category: one of [{categories}]\n"
            f'- topics: array of 1-4 topic tags (e.g. ["LTV", "churn", "cross-sell"])\n'
            f"- entities: array of referenced entities (collection names, field names)\n"
            f"- queryTypes: array from [count, aggregation, lookup, trend, comparison, distribution]\n"
            f"- complexity: one of [simple, moderate, complex]\n"
            f"- intent: one of [exploration, reporting, investigation, monitoring]\n"
            f"- collections: array of MongoDB collections queried\n\n"
            f"Conversation:\n{digest}\n\nJSON:"
        )

        response = await model.ainvoke([HumanMessage(content=classification_prompt)])
        raw = response.content.strip()
        json_match = re.search(r"\{[\s\S]*\}", raw)
        if not json_match:
            logger.warning("Metadata generation returned no JSON for %s", session_id)
            return

        metadata = json.loads(json_match.group())

        update_fields = {
            "title": metadata.get("title", ""),
            "summary": metadata.get("summary", ""),
            "category": metadata.get("category", ""),
            "topics": metadata.get("topics", []),
            "entities": metadata.get("entities", []),
            "queryTypes": metadata.get("queryTypes", []),
            "complexity": metadata.get("complexity", ""),
            "intent": metadata.get("intent", ""),
            "collections": metadata.get("collections", []),
        }

        try:
            embed_text = f"{metadata.get('title', '')} {metadata.get('summary', '')} {digest}"
            embedder = VoyageEmbeddings(
                model=settings.voyage_query_model,
                api_key=settings.voyage_api_key,
                dimensions=settings.voyage_dimensions,
            )
            update_fields["searchEmbedding"] = embedder.embed_query(embed_text)
        except Exception as embed_err:
            logger.warning("Failed to generate search embedding for %s: %s", session_id, embed_err)

        await coll.update_one({"threadId": session_id}, {"$set": update_fields})
        logger.info("Generated metadata for conversation %s: %s", session_id, metadata.get("title", ""))

    except Exception as e:
        logger.error("Failed to generate conversation metadata: %s", e, exc_info=True)


# ---------------------------------------------------------------------------
# History & Retrieval
# ---------------------------------------------------------------------------

async def get_history(session_id: str) -> list[dict]:
    """Read conversation history from chat_conversations."""
    db = get_db()
    doc = await db["chat_conversations"].find_one({"threadId": session_id})
    if not doc:
        return []
    return doc.get("messages", [])


async def get_conversation(thread_id: str) -> dict | None:
    """Get full conversation document."""
    db = get_db()
    doc = await db["chat_conversations"].find_one({"threadId": thread_id})
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc


async def resume_conversation(thread_id: str) -> dict | None:
    """Return conversation + verify LangGraph checkpoint exists for resume."""
    conversation = await get_conversation(thread_id)
    if not conversation:
        return None

    checkpointer = get_checkpointer()
    if checkpointer:
        config = {"configurable": {"thread_id": thread_id}}
        try:
            checkpoint_tuple = await checkpointer.aget_tuple(config)
            conversation["hasCheckpoint"] = checkpoint_tuple is not None
        except Exception:
            conversation["hasCheckpoint"] = False
    else:
        conversation["hasCheckpoint"] = False

    return conversation


async def list_conversations(
    agent_type: str | None = None,
    user_id: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """List recent conversations, optionally filtered by agent type and user."""
    db = get_db()
    query: dict = {}
    if agent_type:
        query["agentType"] = agent_type
    if user_id:
        query["userId"] = user_id

    cursor = (
        db["chat_conversations"]
        .find(query, {"messages": 0, "searchEmbedding": 0})
        .sort("updatedAt", -1)
        .limit(limit)
    )
    results = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        results.append(doc)
    return results


# ---------------------------------------------------------------------------
# Demo Users
# ---------------------------------------------------------------------------

DEMO_USERS = [
    {
        "userId": "analyst-1",
        "name": "Aisha Tan",
        "role": "CRM Analytics Lead",
        "avatar": "AT",
        "department": "Customer Intelligence",
        "focus": "churn, retention, cross-entity migration",
        "preferences": {
            "format": "Always show percentages alongside raw counts",
            "focus_segments": ["tri_entity", "retail_credit"],
            "focus_states": ["Selangor", "Kuala Lumpur"],
            "reporting_style": "Executive summary with bullet points",
        },
        "copilot_suggestions": [
            "What is the churn risk distribution across tiers?",
            "How many tri-entity customers are in Selangor vs KL?",
            "Compare average LTV for retail_credit vs credit_bank segments",
            "Which Gold tier customers have churn risk above 0.7?",
            "Show me the top 10 highest-LTV customers using all three entities",
        ],
        "insights_suggestions": [
            "Which grocery brands have the highest revenue YTD?",
            "Compare health_beauty vs household category performance",
            "What products are in clearance stage with the most inventory?",
            "Show revenue breakdown by product lifecycle stage",
            "Which electronics brands are in the growing stage?",
        ],
    },
    {
        "userId": "analyst-2",
        "name": "Rajesh Kumar",
        "role": "Category Manager",
        "avatar": "RK",
        "department": "Product & Merchandising",
        "focus": "product performance, pricing, supplier analytics",
        "preferences": {
            "format": "Show data as tables with MYR currency formatting",
            "focus_categories": ["electronics", "grocery"],
            "focus_brands": ["Samsung", "Nestle"],
            "reporting_style": "Detailed with actionable recommendations",
        },
        "copilot_suggestions": [
            "How many customers shop at RetailGroup Bukit Tinggi vs RetailGroup Mid Valley?",
            "What is the average transaction value by entity (RetailGroup Co, Credit, Bank)?",
            "Top 5 stores by number of unique customers in Selangor",
            "Show me Silver tier customers in Johor with cross-sell score above 0.6",
            "How many Basic tier customers could be upgraded to Silver?",
        ],
        "insights_suggestions": [
            "What are the top 10 electronics brands by revenue YTD?",
            "How many grocery products are in the mature lifecycle stage?",
            "Compare Asus vs LG vs Huawei total revenue and units sold",
            "Which product categories have the most items in declining stage?",
            "Show average price by category for the top 5 categories",
        ],
    },
    {
        "userId": "analyst-3",
        "name": "Mei Lin Wong",
        "role": "Growth Marketing Manager",
        "avatar": "MW",
        "department": "Marketing & Campaigns",
        "focus": "campaigns, cross-sell, customer acquisition",
        "preferences": {
            "format": "Concise insights with conversion metrics",
            "focus_campaigns": ["cross_sell", "upsell"],
            "focus_tiers": ["Basic", "Silver"],
            "reporting_style": "Campaign-focused with ROI metrics",
        },
        "copilot_suggestions": [
            "How many active cross-sell campaigns are running right now?",
            "What is the average conversion rate across all active campaigns?",
            "Show me Basic tier customers in Penang with high cross-sell score",
            "How many customers are enrolled in the Gold Tier Fast-Track campaign?",
            "Compare customer counts: retail_only vs credit_only vs bank_only",
        ],
        "insights_suggestions": [
            "Which product categories have the most new-stage products?",
            "Show the top 5 brands by units sold YTD in health_beauty",
            "How many products are in the growing lifecycle stage?",
            "Compare fashion vs grocery product counts and total revenue",
            "Which brands have the most clearance-stage products?",
        ],
    },
]

# Pre-seeded memories per user (saved on first startup)
_USER_MEMORIES = {
    "analyst-1": [
        ("format_preference", "Always show percentages alongside raw counts when reporting metrics"),
        ("focus_segments", "Primary segments of interest: tri_entity and retail_credit"),
        ("focus_regions", "Focused on Selangor and Kuala Lumpur markets"),
        ("reporting_style", "Prefers executive summary format with bullet points"),
    ],
    "analyst-2": [
        ("format_preference", "Show data as tables with MYR currency formatting (e.g. RM 1,234.56)"),
        ("focus_categories", "Primary product categories: electronics and grocery"),
        ("focus_brands", "Track Samsung and Nestle performance closely"),
        ("reporting_style", "Prefers detailed analysis with actionable recommendations"),
    ],
    "analyst-3": [
        ("format_preference", "Keep insights concise with conversion metrics highlighted"),
        ("focus_campaigns", "Focused on cross_sell and upsell campaign types"),
        ("focus_tiers", "Primary tier focus: Basic and Silver for upgrade opportunities"),
        ("reporting_style", "Campaign-focused reports with ROI and conversion rate metrics"),
    ],
}


async def seed_app_users():
    """Upsert demo users into app_users collection on startup."""
    db = get_db()
    coll = db["app_users"]
    for user in DEMO_USERS:
        await coll.update_one(
            {"userId": user["userId"]},
            {"$set": user},
            upsert=True,
        )
    logger.info("Seeded %d demo users into app_users", len(DEMO_USERS))


async def seed_user_memories():
    """Pre-populate long-term memories for each demo user (idempotent)."""
    from backend.services.memory_service import get_memory_store

    store = get_memory_store()
    if not store:
        logger.warning("Memory store not available, skipping memory seeding")
        return

    for user_id, memories in _USER_MEMORIES.items():
        namespace = ("user", user_id, "preferences")
        for key, content in memories:
            try:
                existing = await store.asearch(namespace, query=key, limit=1)
                already = any(item.key == key for item in existing)
                if not already:
                    await store.aput(namespace, key, {"content": content})
            except Exception:
                await store.aput(namespace, key, {"content": content})
        logger.info("Seeded %d memories for user %s", len(memories), user_id)


async def get_users() -> list[dict]:
    """Return all app users."""
    db = get_db()
    users = []
    async for doc in db["app_users"].find({}, {"_id": 0}):
        users.append(doc)
    return users
