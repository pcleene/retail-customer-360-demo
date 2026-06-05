"""Seed baseline realtime_kpis collection for anomaly detection."""

import asyncio
import random
from datetime import datetime, timedelta

from pymongo import AsyncMongoClient

from backend.config import settings
from backend.seed.helpers import RetailGroup_STORES, PRODUCT_CATEGORIES

NOW = datetime(2026, 4, 13)
CATEGORIES = list(PRODUCT_CATEGORIES.keys())
RETAIL_STORES = [s for s in RetailGroup_STORES if not s["store_id"].startswith(("ACR-", "ABK-"))]


def generate_kpis(hours: int = 168) -> list[dict]:
    """Generate hourly KPI windows for the last `hours` hours (default 7 days)."""
    kpis = []
    for h in range(hours):
        window_start = NOW - timedelta(hours=hours - h)
        window_end = window_start + timedelta(hours=1)

        # Hour-of-day multiplier (peak 10am-9pm)
        hour = window_start.hour
        if 10 <= hour <= 21:
            multiplier = random.uniform(1.2, 2.0)
        elif 22 <= hour or hour <= 6:
            multiplier = random.uniform(0.1, 0.4)
        else:
            multiplier = random.uniform(0.6, 1.0)

        # Weekend boost
        if window_start.weekday() >= 5:
            multiplier *= 1.3

        base_gmv = 50000 * multiplier
        base_txns = int(200 * multiplier)
        total_gmv = round(base_gmv * random.uniform(0.8, 1.2), 2)
        txn_count = int(base_txns * random.uniform(0.8, 1.2))
        avg_basket = round(total_gmv / max(txn_count, 1), 2)

        # By category
        by_category = []
        for cat in CATEGORIES:
            cat_share = {"grocery": 0.35, "electronics": 0.15, "fashion": 0.15, "household": 0.15, "health_beauty": 0.20}
            share = cat_share.get(cat, 0.2) * random.uniform(0.7, 1.3)
            cat_gmv = round(total_gmv * share, 2)
            cat_txns = max(1, int(txn_count * share))
            by_category.append({
                "category": cat,
                "gmv_myr": cat_gmv,
                "txn_count": cat_txns,
                "avg_basket_myr": round(cat_gmv / cat_txns, 2),
            })

        # By store (top 10)
        by_store = []
        store_sample = random.sample(RETAIL_STORES, k=min(10, len(RETAIL_STORES)))
        for s in store_sample:
            s_gmv = round(total_gmv * random.uniform(0.02, 0.08), 2)
            s_txns = max(1, int(txn_count * random.uniform(0.02, 0.08)))
            by_store.append({"store_id": s["store_id"], "gmv_myr": s_gmv, "txn_count": s_txns})

        # Daily average for anomaly detection (historical baseline)
        daily_avg_gmv = round(50000 * 14, 2)  # rough 14-hour active period
        velocity_ratio = round(total_gmv / (daily_avg_gmv / 14), 2) if daily_avg_gmv > 0 else 1.0

        kpis.append({
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
            "total_gmv_myr": total_gmv,
            "txn_count": txn_count,
            "avg_basket_myr": avg_basket,
            "by_category": by_category,
            "by_store": by_store,
            "daily_avg_gmv_myr": daily_avg_gmv,
            "velocity_ratio": velocity_ratio,
        })

    return kpis


async def seed_realtime_kpis():
    print("Generating realtime KPIs (7 days of hourly windows)...")
    kpis = generate_kpis(168)

    client = AsyncMongoClient(settings.mongodb_uri)
    db = client[settings.mongodb_db]
    coll = db["realtime_kpis"]
    await coll.drop()
    await coll.insert_many(kpis)
    print(f"Seeded {len(kpis)} hourly KPI windows")
    await client.close()


if __name__ == "__main__":
    asyncio.run(seed_realtime_kpis())
