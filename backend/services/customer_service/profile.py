"""Single customer fetch and transaction queries."""

import random
import time
from datetime import datetime, timedelta

from backend.database import get_db
from backend.query_log import log_query


def _normalise_customer(doc: dict) -> dict:
    """Fill in any missing computed fields (trend data) for the frontend.

    With the new nested schema, documents already have the correct structure.
    This only backfills trend arrays if the seeder didn't generate them.
    """
    now = datetime(2026, 4, 13)

    cem = doc.get("cross_entity_metrics", {})
    if not cem.get("ltv_trend"):
        base = cem.get("total_ltv", 1000) * 0.7
        trend = []
        for i in range(12):
            month_dt = now - timedelta(days=30 * (11 - i))
            base = base * (1 + random.uniform(-0.05, 0.1))
            trend.append({"month": month_dt.strftime("%Y-%m"), "value": round(base, 2)})
        cem["ltv_trend"] = trend

    if not cem.get("monthly_spend_trend"):
        avg_spend = cem.get("total_ltv", 1000) / 24
        trend = []
        for i in range(12):
            month_dt = now - timedelta(days=30 * (11 - i))
            val = avg_spend * random.uniform(0.5, 1.6)
            trend.append({"month": month_dt.strftime("%Y-%m"), "value": round(val, 2)})
        cem["monthly_spend_trend"] = trend

    doc["cross_entity_metrics"] = cem

    if "active_campaigns" not in doc:
        doc["active_campaigns"] = []

    return doc


async def get_customer_by_id(customer_id: str) -> dict | None:
    """Fetch a single customer by ID (full document, no embedding)."""
    db = get_db()
    filt = {"customer_id": customer_id}
    proj = {"_id": 0, "embedding": 0, "embedding_text": 0}
    t0 = time.perf_counter()
    doc = await db["customers"].find_one(filt, proj)
    elapsed = (time.perf_counter() - t0) * 1000
    log_query("customers", "find_one", {"filter": filt, "projection": proj}, elapsed, result=doc)
    if doc is None:
        return None
    return _normalise_customer(doc)


async def get_customer_transactions(customer_id: str, limit: int = 50) -> list[dict]:
    """Fetch recent transactions for a customer."""
    db = get_db()
    filt = {"customer_id": customer_id}
    t0 = time.perf_counter()
    results: list[dict] = []
    async for doc in db["transactions"].find(filt, {"_id": 0}).sort("date", -1).limit(limit):
        results.append(doc)
    elapsed = (time.perf_counter() - t0) * 1000
    log_query(
        "transactions", "find",
        {"filter": filt, "sort": {"date": -1}, "limit": limit, "projection": {"_id": 0}},
        elapsed,
        result=results,
    )
    return results
