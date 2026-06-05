"""Campaign service — matching, enrollment management."""

import time

from backend.database import get_db
from backend.query_log import log_query
from backend.services.embedding_service import embed_for_query, rerank


async def get_campaigns(status: str | None = None) -> list[dict]:
    db = get_db()
    query = {}
    if status:
        query["status"] = status
    results = []
    t0 = time.perf_counter()
    async for doc in db["campaigns"].find(query, {"_id": 0, "embedding": 0}).sort("campaign_id", 1):
        results.append(doc)
    log_query("campaigns", "find", {"filter": query, "sort": {"campaign_id": 1}}, (time.perf_counter() - t0) * 1000)
    return results


async def get_campaign_by_id(campaign_id: str) -> dict | None:
    db = get_db()
    filt = {"campaign_id": campaign_id}
    t0 = time.perf_counter()
    doc = await db["campaigns"].find_one(filt, {"_id": 0, "embedding": 0})
    log_query("campaigns", "find_one", {"filter": filt}, (time.perf_counter() - t0) * 1000)
    return doc


async def vector_match_campaigns(customer_text: str, top_k: int = 5, status: str = "active") -> list[dict]:
    """Vector search for campaigns matching a customer profile."""
    db = get_db()
    query_emb = embed_for_query(customer_text)

    pipeline = [
        {
            "$vectorSearch": {
                "index": "campaigns_vector",
                "path": "embedding",
                "queryVector": query_emb,
                "numCandidates": top_k * 10,
                "limit": top_k * 2,
                "filter": {"status": status},
            }
        },
        {"$addFields": {"similarity_score": {"$meta": "vectorSearchScore"}}},
        {"$project": {"_id": 0, "embedding": 0}},
    ]

    candidates = []
    t0 = time.perf_counter()
    async for doc in await db["campaigns"].aggregate(pipeline):
        candidates.append(doc)
    log_query("campaigns", "aggregate", pipeline, (time.perf_counter() - t0) * 1000)

    if not candidates:
        return []

    # Rerank with Voyage
    docs_text = [f"{c['name']} {c['description']}" for c in candidates]
    reranked = rerank(customer_text, docs_text, top_k=top_k)

    results = []
    for r in reranked:
        camp = candidates[r["index"]]
        camp["rerank_score"] = r["relevance_score"]
        results.append(camp)

    return results


async def vector_match_content(customer_campaign_text: str, campaign_id: str, top_k: int = 3) -> list[dict]:
    """Vector search for content assets matching customer x campaign."""
    db = get_db()
    query_emb = embed_for_query(customer_campaign_text)

    pipeline = [
        {
            "$vectorSearch": {
                "index": "content_vector",
                "path": "embedding",
                "queryVector": query_emb,
                "numCandidates": top_k * 10,
                "limit": top_k,
                "filter": {"campaign_id": campaign_id},
            }
        },
        {"$addFields": {"similarity_score": {"$meta": "vectorSearchScore"}}},
        {"$project": {"_id": 0, "embedding": 0}},
    ]

    results = []
    t0 = time.perf_counter()
    async for doc in await db["content_assets"].aggregate(pipeline):
        results.append(doc)
    log_query("content_assets", "aggregate", pipeline, (time.perf_counter() - t0) * 1000)
    return results


async def get_campaign_enrollments(campaign_id: str) -> list[dict]:
    """Get all customers enrolled in a campaign."""
    db = get_db()
    filt = {"active_campaigns.campaign_id": campaign_id}
    proj = {"_id": 0, "customer_id": 1, "unified_profile.name": 1, "tier": 1,
            "segment": 1, "unified_profile.address.state": 1,
            "cross_entity_metrics.total_ltv": 1, "active_campaigns.$": 1}
    results = []
    t0 = time.perf_counter()
    async for doc in db["customers"].find(filt, proj):
        results.append(doc)
    log_query("customers", "find", {"filter": filt, "projection": proj}, (time.perf_counter() - t0) * 1000)
    return results


async def enroll_customer(customer_id: str, enrollment: dict) -> bool:
    """Add a campaign enrollment to a customer's active_campaigns."""
    db = get_db()
    result = await db["customers"].update_one(
        {"customer_id": customer_id},
        {"$push": {"active_campaigns": enrollment}},
    )
    # Update campaign enrollment count
    if result.modified_count > 0:
        await db["campaigns"].update_one(
            {"campaign_id": enrollment["campaign_id"]},
            {"$inc": {"performance.enrollment_count": 1}},
        )
    return result.modified_count > 0
