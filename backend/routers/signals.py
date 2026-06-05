"""SSE endpoint for real-time signal streaming."""

import asyncio
import json
import random
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks
from sse_starlette.sse import EventSourceResponse

from backend.database import get_db

router = APIRouter(prefix="/api/signals", tags=["signals"])

SIGNAL_TYPES = [
    "high_cross_sell_score",
    "churn_risk_spike",
    "tier_upgrade_eligible",
    "dormant_high_value",
    "cross_entity_opportunity",
    "seasonal_spending_pattern",
]


async def _signal_generator():
    """Watch cross_sell_signals collection for new inserts and yield SSE events."""
    db = get_db()
    coll = db["cross_sell_signals"]

    # Use change stream if available, otherwise poll
    try:
        async with await coll.watch(
            [{"$match": {"operationType": "insert"}}],
            full_document="updateLookup",
        ) as stream:
            async for change in stream:
                doc = change.get("fullDocument", {})
                doc.pop("_id", None)
                yield {"data": json.dumps(doc, default=str)}
    except Exception:
        # Fallback: polling for free-tier clusters that don't support change streams
        last_check = datetime.now().isoformat()
        while True:
            await asyncio.sleep(2)
            cursor = coll.find(
                {"created_at": {"$gt": last_check}},
                {"_id": 0},
            ).sort("created_at", 1)
            async for doc in cursor:
                last_check = doc.get("created_at", last_check)
                yield {"data": json.dumps(doc, default=str)}


@router.get("/stream")
async def signal_stream():
    return EventSourceResponse(_signal_generator())


async def _insert_signals(count: int, interval: float):
    """Insert synthetic signals at regular intervals."""
    db = get_db()
    coll = db["cross_sell_signals"]
    for i in range(count):
        customer_idx = random.randint(1, 50000)
        signal = {
            "customer_id": f"CUST-{customer_idx:06d}",
            "signal_type": random.choice(SIGNAL_TYPES),
            "score": round(random.uniform(0.3, 0.95), 3),
            "details": f"Auto-detected signal #{i+1}",
            "processed": False,
            "created_at": datetime.now().isoformat(),
        }
        await coll.insert_one(signal)
        await asyncio.sleep(interval)


@router.post("/simulate")
async def simulate_signals(background_tasks: BackgroundTasks, count: int = 20, interval: float = 3.0):
    """Start inserting synthetic signals in the background."""
    background_tasks.add_task(_insert_signals, count, interval)
    return {"status": "started", "count": count, "interval_seconds": interval}
