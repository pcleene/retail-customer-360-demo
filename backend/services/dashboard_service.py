"""Dashboard KPI aggregations.

Handles both legacy flat documents (cross_sell_score at top level)
and new nested documents (cross_entity_metrics.cross_sell_score).
Uses $ifNull to coalesce both field paths.
"""

import time

from backend.database import get_db
from backend.query_log import log_query

_XS = {"$ifNull": ["$cross_entity_metrics.cross_sell_score", "$cross_sell_score", 0]}
_CHURN = {"$ifNull": ["$cross_entity_metrics.churn_risk", "$churn_risk", 0]}
_LTV = {"$ifNull": ["$cross_entity_metrics.total_ltv", "$ltv_myr", 0]}


async def get_dashboard_kpis() -> dict:
    db = get_db()
    cust = db["customers"]
    camp = db["campaigns"]
    signals = db["cross_sell_signals"]

    t0 = time.perf_counter()
    total_customers = await cust.count_documents({})
    log_query("customers", "count_documents", {}, (time.perf_counter() - t0) * 1000)

    opp_pipeline = [
        {"$addFields": {"_xs": _XS}},
        {"$match": {"_xs": {"$gte": 0.6}}},
        {"$count": "n"},
    ]
    total_opportunities = 0
    t0 = time.perf_counter()
    async for doc in await cust.aggregate(opp_pipeline):
        total_opportunities = doc["n"]
    log_query("customers", "aggregate", opp_pipeline, (time.perf_counter() - t0) * 1000)

    t0 = time.perf_counter()
    active_campaigns = await camp.count_documents({"status": "active"})
    log_query("campaigns", "count_documents", {"status": "active"}, (time.perf_counter() - t0) * 1000)

    avg_conv_pipeline = [
        {"$match": {"status": "active"}},
        {"$group": {"_id": None, "avg_rate": {"$avg": "$performance.conversion_rate"}}},
    ]
    avg_conv = 0.0
    t0 = time.perf_counter()
    async for doc in await camp.aggregate(avg_conv_pipeline):
        avg_conv = round(doc.get("avg_rate") or 0, 4)
    log_query("campaigns", "aggregate", avg_conv_pipeline, (time.perf_counter() - t0) * 1000)

    seg_pipeline = [{"$group": {"_id": "$segment", "count": {"$sum": 1}}}]
    by_segment: dict = {}
    t0 = time.perf_counter()
    async for doc in await cust.aggregate(seg_pipeline):
        if doc["_id"]:
            by_segment[doc["_id"]] = doc["count"]
    log_query("customers", "aggregate", seg_pipeline, (time.perf_counter() - t0) * 1000)

    tier_pipeline = [{"$group": {"_id": "$tier", "count": {"$sum": 1}}}]
    by_tier: dict = {}
    t0 = time.perf_counter()
    async for doc in await cust.aggregate(tier_pipeline):
        if doc["_id"]:
            by_tier[doc["_id"]] = doc["count"]
    log_query("customers", "aggregate", tier_pipeline, (time.perf_counter() - t0) * 1000)

    xs_pipeline = [
        {"$group": {"_id": "$tier", "avg_score": {"$avg": _XS}}},
    ]
    avg_xs_by_tier: dict = {}
    t0 = time.perf_counter()
    async for doc in await cust.aggregate(xs_pipeline):
        if doc["_id"]:
            avg_xs_by_tier[doc["_id"]] = round(doc["avg_score"] or 0, 3)
    log_query("customers", "aggregate", xs_pipeline, (time.perf_counter() - t0) * 1000)

    churn_pipeline = [
        {"$group": {"_id": "$tier", "avg_churn": {"$avg": _CHURN}}},
    ]
    avg_churn_by_tier: dict = {}
    t0 = time.perf_counter()
    async for doc in await cust.aggregate(churn_pipeline):
        if doc["_id"]:
            avg_churn_by_tier[doc["_id"]] = round(doc["avg_churn"] or 0, 3)
    log_query("customers", "aggregate", churn_pipeline, (time.perf_counter() - t0) * 1000)

    ltv_pipeline = [
        {"$group": {"_id": "$segment", "avg_ltv": {"$avg": _LTV}}},
    ]
    avg_ltv_by_segment: dict = {}
    t0 = time.perf_counter()
    async for doc in await cust.aggregate(ltv_pipeline):
        if doc["_id"]:
            avg_ltv_by_segment[doc["_id"]] = round(doc["avg_ltv"] or 0, 2)
    log_query("customers", "aggregate", ltv_pipeline, (time.perf_counter() - t0) * 1000)

    recent_signals: list = []
    t0 = time.perf_counter()
    async for doc in signals.find({}, {"_id": 0}).sort("created_at", -1).limit(20):
        recent_signals.append(doc)
    log_query("cross_sell_signals", "find", {"filter": {}, "sort": {"created_at": -1}, "limit": 20}, (time.perf_counter() - t0) * 1000)

    return {
        "total_customers": total_customers,
        "total_opportunities": total_opportunities,
        "active_campaigns": active_campaigns,
        "avg_conversion_rate": avg_conv,
        "customers_by_segment": by_segment,
        "customers_by_tier": by_tier,
        "avg_cross_sell_by_tier": avg_xs_by_tier,
        "avg_churn_by_tier": avg_churn_by_tier,
        "avg_ltv_by_segment": avg_ltv_by_segment,
        "recent_signals": recent_signals,
    }
