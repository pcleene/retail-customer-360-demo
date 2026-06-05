"""Master seed script — run all seeders in order."""

import asyncio
import time

from backend.seed.seed_stores import seed_stores
from backend.seed.seed_campaigns import seed_campaigns
from backend.seed.seed_thresholds import seed_thresholds
from backend.seed.seed_customers import seed_customers
from backend.seed.seed_campaign_actions import seed_campaign_actions
from backend.seed.seed_transactions import seed_transactions
from backend.seed.seed_products import seed_products
from backend.seed.seed_realtime_kpis import seed_realtime_kpis
from backend.seed.create_indexes import main as create_indexes


async def seed_all():
    start = time.time()
    print("=" * 60)
    print("Retail Customer 360 — Full Data Seed")
    print("=" * 60)

    # Small collections first
    print("\n--- Stores ---")
    await seed_stores()

    print("\n--- Thresholds ---")
    await seed_thresholds()

    print("\n--- Campaigns + Content Assets ---")
    await seed_campaigns()

    # Large collections
    print("\n--- Customers (50K) ---")
    await seed_customers()

    print("\n--- Campaign actions (~5K audit log) ---")
    await seed_campaign_actions()

    print("\n--- Products (500K) ---")
    await seed_products()

    print("\n--- Transactions (2M) ---")
    await seed_transactions()

    print("\n--- Realtime KPIs ---")
    await seed_realtime_kpis()

    # Create indexes after data is loaded
    print("\n--- Creating Indexes ---")
    await create_indexes()

    elapsed = time.time() - start
    print("\n" + "=" * 60)
    print(f"Seed complete in {elapsed:.0f}s ({elapsed/60:.1f}min)")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(seed_all())
