"""Signal simulator — inserts synthetic cross-sell signals for demo."""

import asyncio
import random
from datetime import datetime

from pymongo import AsyncMongoClient

from backend.config import settings

SIGNAL_TYPES = [
    "high_cross_sell_score",
    "churn_risk_spike",
    "tier_upgrade_eligible",
    "dormant_high_value",
    "cross_entity_opportunity",
    "seasonal_spending_pattern",
]


async def simulate_signals(interval: float = 5.0, count: int = 100):
    """Insert signals at regular intervals."""
    client = AsyncMongoClient(settings.mongodb_uri)
    db = client[settings.mongodb_db]
    coll = db["cross_sell_signals"]

    print(f"Starting signal simulator: {count} signals at {interval}s intervals")

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
        print(f"  Signal {i+1}/{count}: {signal['signal_type']} for {signal['customer_id']} (score: {signal['score']})")
        await asyncio.sleep(interval)

    await client.close()
    print("Simulator complete")


if __name__ == "__main__":
    asyncio.run(simulate_signals(interval=3.0, count=50))
