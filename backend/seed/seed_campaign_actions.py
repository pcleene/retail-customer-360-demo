"""Seed historical campaign_actions audit log (~5K) aligned with customer active_campaigns."""

from __future__ import annotations

import asyncio
import random
import secrets
from datetime import datetime, timedelta

from pymongo import AsyncMongoClient

from backend.config import settings

NOW = datetime(2026, 4, 14)
TARGET_COUNT = 5000

REASONING_NODES = [
    "classify_intent",
    "fetch_profile",
    "analyze_patterns",
    "vector_search_customers",
    "vector_search_campaigns",
    "vector_search_content",
    "analyze_similar_conversions",
    "determine_channel",
    "rerank_results",
    "generate_recommendations",
    "execute_actions",
]

NODE_SUMMARIES = {
    "classify_intent": "Routed to individual customer recommendation flow",
    "fetch_profile": "Loaded unified profile and cross-entity metrics",
    "analyze_patterns": "Identified spend velocity and engagement pattern",
    "vector_search_customers": "Retrieved lookalike converters from vector index",
    "vector_search_campaigns": "Ranked campaigns by semantic + targeting affinity",
    "vector_search_content": "Selected best-fitting content asset for channel",
    "analyze_similar_conversions": "Estimated conversion rate from lookalike cohort",
    "determine_channel": "Selected channel by historical CVR",
    "rerank_results": "Applied cross-encoder rerank on shortlist",
    "generate_recommendations": "LLM composed rationale and value proposition",
    "execute_actions": "Persisted enrollment and audit log entry",
}


def _enrolled_by_to_triggered_by(enrolled_by: str) -> str:
    if enrolled_by == "auto_signal":
        return "signal"
    if enrolled_by == "manual":
        return "manual"
    return "agent"


def _cust_suffix(customer_id: str) -> str:
    # CUST-000042 -> cust000042
    part = customer_id.split("-")[-1]
    return f"cust{int(part):06d}"


def _reasoning_steps(anchor: datetime, n_steps: int) -> list[dict]:
    n_steps = min(max(n_steps, 5), 11)
    nodes = REASONING_NODES[:n_steps]
    steps = []
    t = anchor
    for node in nodes:
        dur_s = random.randint(1, 4)
        started = t
        t = t + timedelta(seconds=dur_s)
        steps.append({
            "node": node,
            "started_at": started.strftime("%Y-%m-%dT%H:%M:%S"),
            "finished_at": t.strftime("%Y-%m-%dT%H:%M:%S"),
            "summary": NODE_SUMMARIES.get(node, f"{node} step completed"),
            "details": {},
        })
    return steps


def _doc_from_enrollment(
    customer: dict,
    ac: dict,
    *,
    synthetic: bool,
) -> dict:
    customer_id = customer["customer_id"]
    name = customer.get("unified_profile", {}).get("name", "Customer")
    enrolled_date = ac.get("enrolled_date", NOW.strftime("%Y-%m-%d"))
    enrolled_day = datetime.strptime(enrolled_date[:10], "%Y-%m-%d")
    triggered = _enrolled_by_to_triggered_by(ac.get("enrolled_by", "agent"))

    created = enrolled_day + timedelta(
        hours=random.randint(9, 21),
        minutes=random.randint(0, 59),
        seconds=random.randint(0, 59),
    )
    created_at = created.strftime("%Y-%m-%dT%H:%M:%S")

    status = ac.get("status", "enrolled")
    converted_at = ac.get("converted_at")
    revenue_r = float(ac.get("revenue_realized_myr") or 0.0)

    if synthetic:
        if random.random() < 0.30:
            status = "converted"
            if not converted_at:
                cdt = created + timedelta(days=random.randint(1, 45))
                converted_at = cdt.strftime("%Y-%m-%d")
                uplift = float(ac.get("expected_ltv_uplift") or random.uniform(200, 4000))
                revenue_r = round(uplift * random.uniform(0.6, 1.4), 2)
        else:
            status = random.choice(["enrolled", "sent", "opened", "clicked", "expired"])
            converted_at = None
            revenue_r = 0.0

    last_updated = created + timedelta(hours=random.randint(0, 72), minutes=random.randint(0, 59))
    if status == "converted" and converted_at:
        cdt = datetime.strptime(converted_at[:10], "%Y-%m-%d")
        last_updated = max(last_updated, cdt + timedelta(hours=random.randint(10, 22)))

    signal_id = ac.get("signal_id") if triggered == "signal" else None
    if synthetic and triggered == "signal" and not signal_id:
        signal_id = f"SIG-{created.strftime('%Y%m%d')}-{random.randint(1, 999_999):06d}"

    ymd = created.strftime("%Y%m%d")
    action_id = f"ACT-{ymd}-000000"

    agent_thread_id = f"thr_{ymd}_{_cust_suffix(customer_id)}_{secrets.token_hex(3)}"

    n_steps = random.randint(5, 11)
    steps = _reasoning_steps(created - timedelta(seconds=25), n_steps)

    sim_rate = float(ac.get("similar_customer_conversion_rate") or random.uniform(0.05, 0.22))
    uplift = float(ac.get("expected_ltv_uplift") or random.uniform(150, 4500))

    return {
        "action_id": action_id,
        "enrollment_id": ac["enrollment_id"],
        "customer_id": customer_id,
        "customer_name_snapshot": name,
        "campaign_id": ac["campaign_id"],
        "campaign_name_snapshot": ac.get("campaign_name", ""),
        "content_id": ac.get("content_asset_id"),
        "recommended_channel": ac.get("recommended_channel", "email"),
        "triggered_by": triggered,
        "signal_id": signal_id,
        "agent_thread_id": agent_thread_id,
        "reasoning": ac.get("reasoning") or (
            f"Synthetic audit: {triggered} path; campaign fit from vector + rules engine."
        ),
        "reasoning_steps": steps,
        "similar_customers_sampled": ac.get("similar_customers_sampled") or [],
        "similar_conversion_rate": sim_rate,
        "expected_ltv_uplift": uplift,
        "targeting_match_score": round(random.uniform(0.55, 0.98), 3),
        "semantic_similarity": round(random.uniform(0.5, 0.95), 3),
        "rerank_score": round(random.uniform(0.55, 0.95), 3),
        "status": status,
        "created_at": created_at,
        "last_updated_at": last_updated.strftime("%Y-%m-%dT%H:%M:%S"),
        "converted_at": converted_at if status == "converted" else None,
        "revenue_realized_myr": revenue_r if status == "converted" else 0.0,
    }


async def seed_campaign_actions():
    client = AsyncMongoClient(settings.mongodb_uri)
    db = client[settings.mongodb_db]
    cust_coll = db["customers"]
    camp_coll = db["campaigns"]

    campaign_rows = await camp_coll.find(
        {},
        {"campaign_id": 1, "name": 1, "content_assets": 1},
    ).to_list(length=None)
    if not campaign_rows:
        campaign_rows = [
            {
                "campaign_id": f"CMP-{i:04d}",
                "name": f"Placeholder Campaign {i}",
                "content_assets": [f"CNT-{((i - 1) * 4 + j + 1):05d}" for j in range(4)],
            }
            for i in range(1, 31)
        ]

    cur = cust_coll.find(
        {"active_campaigns": {"$exists": True, "$ne": []}},
        {
            "customer_id": 1,
            "unified_profile.name": 1,
            "active_campaigns": 1,
        },
    )
    customers = await cur.to_list(length=None)

    actions: list[dict] = []

    for c in customers:
        for ac in c.get("active_campaigns") or []:
            actions.append(_doc_from_enrollment(c, ac, synthetic=False))

    if len(actions) > TARGET_COUNT:
        random.shuffle(actions)
        actions = actions[:TARGET_COUNT]

    shortfall = TARGET_COUNT - len(actions)
    if shortfall > 0:
        all_cust = await cust_coll.find(
            {},
            {"customer_id": 1, "unified_profile.name": 1},
        ).to_list(length=None)
        if not all_cust:
            all_cust = [{"customer_id": f"CUST-{i:06d}", "unified_profile": {"name": "Synthetic"}} for i in range(1, 1001)]

        for _ in range(shortfall):
            cust = random.choice(all_cust)
            camp = random.choice(campaign_rows)
            assets = camp.get("content_assets") or []
            ch = random.choice(
                ["email", "sms", "whatsapp", "in_app", "push_notification"],
            )
            enrolled_by = random.choices(
                ["agent", "manual", "auto_signal"],
                weights=[0.45, 0.25, 0.30],
                k=1,
            )[0]
            enr_day = NOW - timedelta(days=random.randint(1, 400))
            enrollment_id = f"ENR-{enr_day.strftime('%Y%m%d')}-{random.randint(1, 999_999):06d}"
            peer_ids = [x["customer_id"] for x in random.sample(all_cust, k=min(5, len(all_cust)))]
            peer_ids = [p for p in peer_ids if p != cust["customer_id"]][:5]

            ac = {
                "campaign_id": camp["campaign_id"],
                "campaign_name": camp.get("name", "Campaign"),
                "enrollment_id": enrollment_id,
                "enrolled_date": enr_day.strftime("%Y-%m-%d"),
                "enrolled_by": enrolled_by,
                "signal_id": (
                    f"SIG-{enr_day.strftime('%Y%m%d')}-{random.randint(1, 999_999):06d}"
                    if enrolled_by == "auto_signal"
                    else None
                ),
                "content_asset_id": random.choice(assets) if assets else None,
                "recommended_channel": ch,
                "reasoning": "Synthetic backfill enrollment for dashboard volume.",
                "similar_customer_conversion_rate": round(random.uniform(0.05, 0.22), 2),
                "expected_ltv_uplift": round(random.uniform(200, 5000), 2),
                "similar_customers_sampled": peer_ids,
                "status": "enrolled",
                "converted_at": None,
                "revenue_realized_myr": 0.0,
            }
            actions.append(_doc_from_enrollment(cust, ac, synthetic=True))

    for i, doc in enumerate(actions):
        seq = i + 1
        created = datetime.strptime(doc["created_at"][:19], "%Y-%m-%dT%H:%M:%S")
        ymd = created.strftime("%Y%m%d")
        doc["action_id"] = f"ACT-{ymd}-{seq:06d}"

    coll = db["campaign_actions"]
    await coll.drop()
    if actions:
        await coll.insert_many(actions)

    print(f"Seeded {len(actions)} campaign_actions")
    await client.close()


if __name__ == "__main__":
    asyncio.run(seed_campaign_actions())
