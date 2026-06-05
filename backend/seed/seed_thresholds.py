"""Seed threshold rules and sample cross-sell signals (alert documents)."""

import asyncio
import random
from datetime import datetime, timedelta

from pymongo import AsyncMongoClient

from backend.config import settings

NOW = datetime(2026, 4, 14, 12, 0, 0)
SIGNAL_TYPES = [
    "high_cross_sell_score",
    "churn_risk_spike",
    "tier_upgrade_eligible",
    "dormant_high_value",
    "cross_entity_opportunity",
    "seasonal_spending_pattern",
]

# --- 12 full threshold documents (THR-0001 .. THR-0012) ---
THRESHOLD_SEEDS: list[dict] = [
    {
        "threshold_id": "THR-0001",
        "signal_type": "high_cross_sell_score",
        "name": "High cross-sell score, no RetailGroup Bank",
        "description": "Customer cross-sell score >0.7 and retail/credit footprint — prime for bank acquisition.",
        "severity": "high",
        "criteria": [
            {"field": "cross_entity_metrics.cross_sell_score", "operator": "gte", "value": 0.7, "window": None},
            {"field": "entities", "operator": "in", "value": ["RetailGroup Co", "RetailGroup Credit"], "window": None},
        ],
        "target_segments": ["retail_only", "credit_only", "retail_credit"],
        "target_tiers": ["Silver", "Gold", "Platinum"],
        "target_entities": ["RetailGroup Bank"],
        "action_template": {
            "action_type": "enroll_in_campaign",
            "target_campaign_id": "CMP-0002",
            "notification_channel": "best_engagement_channel",
            "notes": "Recommend RetailGroup Bank Savings Booster via the customer's best-performing channel.",
        },
        "auto_process": True,
        "cooldown_hours": 168,
        "priority": "high",
        "active": True,
        "created_at": "2026-01-10T00:00:00",
        "updated_at": "2026-04-01T00:00:00",
        "metrics": {"fired_count": 842, "processed_count": 801, "conversion_rate": 0.19},
    },
    {
        "threshold_id": "THR-0002",
        "signal_type": "high_cross_sell_score",
        "name": "Ultra-high affinity, tri-entity upsell",
        "description": "Cross-sell score >0.85 on tri-entity Platinum — target premium loyalty accelerator.",
        "severity": "critical",
        "criteria": [
            {"field": "cross_entity_metrics.cross_sell_score", "operator": "gte", "value": 0.85, "window": None},
            {"field": "segment", "operator": "eq", "value": "tri_entity", "window": None},
            {"field": "tier", "operator": "eq", "value": "Platinum", "window": None},
        ],
        "target_segments": ["tri_entity"],
        "target_tiers": ["Platinum"],
        "target_entities": ["RetailGroup Co", "RetailGroup Credit", "RetailGroup Bank"],
        "action_template": {
            "action_type": "enroll_in_campaign",
            "target_campaign_id": "CMP-0003",
            "notification_channel": "in_app",
            "notes": "Tri-entity loyalty accelerator via in-app for highest engagement.",
        },
        "auto_process": True,
        "cooldown_hours": 72,
        "priority": "high",
        "active": True,
        "created_at": "2026-01-12T00:00:00",
        "updated_at": "2026-04-02T00:00:00",
        "metrics": {"fired_count": 312, "processed_count": 298, "conversion_rate": 0.24},
    },
    {
        "threshold_id": "THR-0003",
        "signal_type": "churn_risk_spike",
        "name": "Churn risk breach — Gold tier",
        "description": "Churn risk crossed 0.65 within 30d window for Gold customers.",
        "severity": "critical",
        "criteria": [
            {"field": "cross_entity_metrics.churn_risk", "operator": "gte", "value": 0.65, "window": "30d"},
            {"field": "tier", "operator": "eq", "value": "Gold", "window": None},
        ],
        "target_segments": ["retail_only", "retail_credit", "retail_bank", "tri_entity"],
        "target_tiers": ["Gold"],
        "target_entities": ["RetailGroup Co"],
        "action_template": {
            "action_type": "enroll_in_campaign",
            "target_campaign_id": "CMP-0005",
            "notification_channel": "whatsapp",
            "notes": "Win-back voucher on WhatsApp for at-risk Gold members.",
        },
        "auto_process": True,
        "cooldown_hours": 48,
        "priority": "critical",
        "active": True,
        "created_at": "2026-01-08T00:00:00",
        "updated_at": "2026-03-20T00:00:00",
        "metrics": {"fired_count": 1204, "processed_count": 1150, "conversion_rate": 0.14},
    },
    {
        "threshold_id": "THR-0004",
        "signal_type": "churn_risk_spike",
        "name": "Churn spike — credit portfolio",
        "description": "RetailGroup Credit customers with churn risk >0.7 and rising utilization.",
        "severity": "high",
        "criteria": [
            {"field": "cross_entity_metrics.churn_risk", "operator": "gte", "value": 0.7, "window": "24h"},
            {"field": "entities", "operator": "in", "value": ["RetailGroup Credit"], "window": None},
        ],
        "target_segments": ["credit_only", "retail_credit", "credit_bank", "tri_entity"],
        "target_tiers": ["Silver", "Gold", "Platinum"],
        "target_entities": ["RetailGroup Credit"],
        "action_template": {
            "action_type": "send_alert",
            "target_campaign_id": "CMP-0015",
            "notification_channel": "email",
            "notes": "Balance transfer offer for high churn-risk credit customers.",
        },
        "auto_process": True,
        "cooldown_hours": 96,
        "priority": "high",
        "active": True,
        "created_at": "2026-01-14T00:00:00",
        "updated_at": "2026-03-28T00:00:00",
        "metrics": {"fired_count": 556, "processed_count": 520, "conversion_rate": 0.11},
    },
    {
        "threshold_id": "THR-0005",
        "signal_type": "tier_upgrade_eligible",
        "name": "Spend velocity qualifies for Gold",
        "description": "90d spend trajectory crosses internal Gold threshold for Silver members.",
        "severity": "medium",
        "criteria": [
            {"field": "cross_entity_metrics.monthly_spend_trend", "operator": "gte", "value": 2500.0, "window": "90d"},
            {"field": "tier", "operator": "eq", "value": "Silver", "window": None},
        ],
        "target_segments": ["retail_only", "retail_credit", "retail_bank"],
        "target_tiers": ["Silver"],
        "target_entities": ["RetailGroup Co"],
        "action_template": {
            "action_type": "enroll_in_campaign",
            "target_campaign_id": "CMP-0004",
            "notification_channel": "push_notification",
            "notes": "Gold tier fast-track challenge via push.",
        },
        "auto_process": True,
        "cooldown_hours": 336,
        "priority": "medium",
        "active": True,
        "created_at": "2026-02-01T00:00:00",
        "updated_at": "2026-04-05T00:00:00",
        "metrics": {"fired_count": 2103, "processed_count": 1988, "conversion_rate": 0.22},
    },
    {
        "threshold_id": "THR-0006",
        "signal_type": "tier_upgrade_eligible",
        "name": "Platinum engagement runway",
        "description": "Gold members with LTV trend +8% QoQ eligible for Platinum upgrade messaging.",
        "severity": "medium",
        "criteria": [
            {"field": "cross_entity_metrics.total_ltv", "operator": "gte", "value": 45000.0, "window": None},
            {"field": "tier", "operator": "eq", "value": "Gold", "window": None},
        ],
        "target_segments": ["tri_entity", "retail_credit", "retail_bank"],
        "target_tiers": ["Gold"],
        "target_entities": ["RetailGroup Co", "RetailGroup Credit", "RetailGroup Bank"],
        "action_template": {
            "action_type": "enroll_in_campaign",
            "target_campaign_id": "CMP-0017",
            "notification_channel": "best_engagement_channel",
            "notes": "Platinum exclusive dining — high-touch retention.",
        },
        "auto_process": False,
        "cooldown_hours": 720,
        "priority": "medium",
        "active": True,
        "created_at": "2026-02-10T00:00:00",
        "updated_at": "2026-04-06T00:00:00",
        "metrics": {"fired_count": 428, "processed_count": 390, "conversion_rate": 0.18},
    },
    {
        "threshold_id": "THR-0007",
        "signal_type": "dormant_high_value",
        "name": "High LTV dormant 35+ days",
        "description": "Platinum / high LTV customers with no visit in 35+ days.",
        "severity": "high",
        "criteria": [
            {"field": "cross_entity_metrics.total_ltv", "operator": "gte", "value": 80000.0, "window": None},
            {"field": "last_visit", "operator": "lte", "value": "NOW-35d", "window": "35d"},
        ],
        "target_segments": ["tri_entity", "retail_bank", "credit_bank"],
        "target_tiers": ["Gold", "Platinum"],
        "target_entities": ["RetailGroup Co"],
        "action_template": {
            "action_type": "enroll_in_campaign",
            "target_campaign_id": "CMP-0005",
            "notification_channel": "whatsapp",
            "notes": "Win-back RM50 voucher for dormant premium shoppers.",
        },
        "auto_process": True,
        "cooldown_hours": 168,
        "priority": "high",
        "active": True,
        "created_at": "2026-01-20T00:00:00",
        "updated_at": "2026-04-07T00:00:00",
        "metrics": {"fired_count": 901, "processed_count": 860, "conversion_rate": 0.16},
    },
    {
        "threshold_id": "THR-0008",
        "signal_type": "dormant_high_value",
        "name": "Credit-active, retail dormant",
        "description": "Credit customers with retail dormancy >21 days but active repayment behavior.",
        "severity": "medium",
        "criteria": [
            {"field": "entity_profiles.RetailGroup_credit.payment_history_score", "operator": "gte", "value": 0.85, "window": None},
            {"field": "last_visit", "operator": "lte", "value": "NOW-21d", "window": "21d"},
        ],
        "target_segments": ["credit_only", "retail_credit"],
        "target_tiers": ["Basic", "Silver", "Gold"],
        "target_entities": ["RetailGroup Credit", "RetailGroup Co"],
        "action_template": {
            "action_type": "enroll_in_campaign",
            "target_campaign_id": "CMP-0008",
            "notification_channel": "sms",
            "notes": "Family electronics bundle to re-activate in-store visits.",
        },
        "auto_process": True,
        "cooldown_hours": 120,
        "priority": "medium",
        "active": True,
        "created_at": "2026-01-22T00:00:00",
        "updated_at": "2026-04-08T00:00:00",
        "metrics": {"fired_count": 673, "processed_count": 640, "conversion_rate": 0.12},
    },
    {
        "threshold_id": "THR-0009",
        "signal_type": "cross_entity_opportunity",
        "name": "Tri-entity wealth upsell",
        "description": "Tri-entity Platinum with bank balance and rising LTV — FD / wealth products.",
        "severity": "high",
        "criteria": [
            {"field": "cross_entity_metrics.cross_sell_score", "operator": "gte", "value": 0.75, "window": None},
            {"field": "tier", "operator": "eq", "value": "Platinum", "window": None},
            {"field": "entities", "operator": "in", "value": ["RetailGroup Bank"], "window": None},
            {"field": "entity_profiles.RetailGroup_bank.balance_myr", "operator": "gte", "value": 10000.0, "window": None},
        ],
        "target_segments": ["tri_entity"],
        "target_tiers": ["Platinum"],
        "target_entities": ["RetailGroup Bank"],
        "action_template": {
            "action_type": "enroll_in_campaign",
            "target_campaign_id": "CMP-0007",
            "notification_channel": "best_engagement_channel",
            "notes": "Fixed deposit promo routed to best channel.",
        },
        "auto_process": True,
        "cooldown_hours": 168,
        "priority": "high",
        "active": True,
        "created_at": "2026-01-15T00:00:00",
        "updated_at": "2026-04-01T00:00:00",
        "metrics": {"fired_count": 412, "processed_count": 387, "conversion_rate": 0.21},
    },
    {
        "threshold_id": "THR-0010",
        "signal_type": "cross_entity_opportunity",
        "name": "Retail-only to credit acquisition",
        "description": "Retail-only segment with high basket and low credit penetration.",
        "severity": "medium",
        "criteria": [
            {"field": "segment", "operator": "eq", "value": "retail_only", "window": None},
            {"field": "cross_entity_metrics.cross_sell_score", "operator": "gte", "value": 0.55, "window": None},
        ],
        "target_segments": ["retail_only"],
        "target_tiers": ["Silver", "Gold"],
        "target_entities": ["RetailGroup Credit"],
        "action_template": {
            "action_type": "enroll_in_campaign",
            "target_campaign_id": "CMP-0001",
            "notification_channel": "email",
            "notes": "Credit card cashback fiesta for qualified retail shoppers.",
        },
        "auto_process": True,
        "cooldown_hours": 240,
        "priority": "medium",
        "active": True,
        "created_at": "2026-01-18T00:00:00",
        "updated_at": "2026-04-03T00:00:00",
        "metrics": {"fired_count": 1520, "processed_count": 1422, "conversion_rate": 0.09},
    },
    {
        "threshold_id": "THR-0011",
        "signal_type": "seasonal_spending_pattern",
        "name": "Festival basket match — Raya",
        "description": "Spend pattern matches seasonal grocery / fashion uplift for Raya campaigns.",
        "severity": "low",
        "criteria": [
            {"field": "interaction_history.marketing_interactions", "operator": "gte", "value": 1.0, "window": "30d"},
            {"field": "cross_entity_metrics.monthly_spend_trend", "operator": "gte", "value": 1800.0, "window": "30d"},
        ],
        "target_segments": ["retail_only", "retail_credit", "tri_entity"],
        "target_tiers": ["Basic", "Silver", "Gold", "Platinum"],
        "target_entities": ["RetailGroup Co"],
        "action_template": {
            "action_type": "enroll_in_campaign",
            "target_campaign_id": "CMP-0009",
            "notification_channel": "push_notification",
            "notes": "Raya mega sale — push during peak evening window.",
        },
        "auto_process": False,
        "cooldown_hours": 72,
        "priority": "low",
        "active": True,
        "created_at": "2026-03-01T00:00:00",
        "updated_at": "2026-04-10T00:00:00",
        "metrics": {"fired_count": 2341, "processed_count": 890, "conversion_rate": 0.07},
    },
    {
        "threshold_id": "THR-0012",
        "signal_type": "seasonal_spending_pattern",
        "name": "Travel & insurance seasonal attach",
        "description": "Customers with elevated travel-related category spend in prior 60d.",
        "severity": "low",
        "criteria": [
            {"field": "cross_entity_metrics.cross_sell_score", "operator": "gte", "value": 0.5, "window": "60d"},
            {"field": "tier", "operator": "in", "value": ["Gold", "Platinum"], "window": None},
        ],
        "target_segments": ["retail_credit", "credit_bank", "tri_entity"],
        "target_tiers": ["Gold", "Platinum"],
        "target_entities": ["RetailGroup Credit"],
        "action_template": {
            "action_type": "flag_for_review",
            "target_campaign_id": "CMP-0019",
            "notification_channel": "email",
            "notes": "Insurance bundle cross-sell — manual review for compliance.",
        },
        "auto_process": False,
        "cooldown_hours": 168,
        "priority": "low",
        "active": True,
        "created_at": "2026-03-05T00:00:00",
        "updated_at": "2026-04-11T00:00:00",
        "metrics": {"fired_count": 884, "processed_count": 302, "conversion_rate": 0.05},
    },
]


def _random_customer_id() -> str:
    return f"CUST-{random.randint(1, 50_000):06d}"


def _severity_for_signal_type(st: str) -> str:
    if st in ("churn_risk_spike", "cross_entity_opportunity", "high_cross_sell_score"):
        return random.choices(
            ["low", "medium", "high", "critical"],
            weights=[0.1, 0.25, 0.45, 0.2],
            k=1,
        )[0]
    return random.choices(
        ["low", "medium", "high", "critical"],
        weights=[0.2, 0.35, 0.3, 0.15],
        k=1,
    )[0]


def _build_signal_doc(seq: int) -> dict:
    st = SIGNAL_TYPES[seq % len(SIGNAL_TYPES)]
    thr = THRESHOLD_SEEDS[seq % len(THRESHOLD_SEEDS)]
    threshold_id = thr["threshold_id"]
    customer_id = _random_customer_id()
    day_offset = random.randint(0, 29)
    created = NOW - timedelta(days=day_offset, hours=random.randint(0, 23), minutes=random.randint(0, 59))
    created_at = created.strftime("%Y-%m-%dT%H:%M:%S")
    sig_day = created.strftime("%Y%m%d")
    signal_id = f"SIG-{sig_day}-{seq + 1:06d}"

    sev = _severity_for_signal_type(st)
    score = round(random.uniform(0.45, 0.95), 3)

    titles = {
        "high_cross_sell_score": "Strong cross-sell affinity detected",
        "churn_risk_spike": "Churn risk elevated vs 30d baseline",
        "tier_upgrade_eligible": "Spend pattern qualifies for tier upgrade",
        "dormant_high_value": "High-value customer showing dormancy",
        "cross_entity_opportunity": "Additional entity penetration opportunity",
        "seasonal_spending_pattern": "Seasonal spend pattern matches campaign window",
    }
    title = titles[st]
    description = (
        f"{title} for {customer_id}: score {score:.2f}, severity {sev}. "
        "Automated evaluation suggests enrollment review within SLA."
    )

    n_events = random.randint(1, 3)
    events = []
    for e in range(n_events):
        et = random.choice(["transaction", "channel_engagement", "profile_change", "threshold_breach"])
        ts = (created - timedelta(hours=random.randint(1, 72))).strftime("%Y-%m-%dT%H:%M:%S")
        events.append({
            "event_type": et,
            "event_id": f"EVT-{created.strftime('%Y%m%d')}-{seq:05d}{e}",
            "timestamp": ts,
            "summary": f"Synthetic {et.replace('_', ' ')} contributing to {st}",
            "payload": {"score": score, "signal_type": st},
        })

    tier = random.choice(["Basic", "Silver", "Gold", "Platinum"])
    segment = random.choice(
        ["retail_only", "credit_only", "bank_only", "retail_credit", "retail_bank", "credit_bank", "tri_entity"],
    )
    entities = random.sample(
        ["RetailGroup Co", "RetailGroup Credit", "RetailGroup Bank"],
        k=random.randint(1, 3),
    )
    context = {
        "customer_id": customer_id,
        "tier": tier,
        "segment": segment,
        "entities": entities,
        "total_ltv": round(random.uniform(2000, 180000), 2),
        "cross_sell_score": round(random.uniform(0.3, 0.95), 3),
        "churn_risk": round(random.uniform(0.05, 0.85), 3),
        "primary_store_id": random.choice(
            ["RetailGroup-1UT", "RetailGroup-MOV", "RetailGroup-QBM", "MXV-PJ1", "RetailGroup-IPH"],
        ),
    }

    rule_snapshot = {
        "threshold_id": threshold_id,
        "signal_type": st,
        "threshold_value": random.choice([0.5, 0.6, 0.65, 0.7, 0.75, 0.8]),
        "operator": random.choice(["gte", "lte", "between"]),
        "window": random.choice(["1h", "24h", "7d", "30d", "90d"]),
        "description": thr["description"],
    }

    camp_id = thr["action_template"].get("target_campaign_id") or f"CMP-{random.randint(1, 30):04d}"
    pool = [
        f"Enroll in campaign {camp_id} via best channel",
        "Send personalized offer within 48 hours",
        "Schedule agent callback if severity is high",
        "Flag for relationship manager review",
    ]
    k = random.randint(2, 3)
    suggested_actions = random.sample(pool, k=k)

    processed = random.random() < 0.60
    processed_at = None
    processed_by = None
    enrollment_id = None
    result = None
    if processed:
        processed_at = (created + timedelta(minutes=random.randint(5, 240))).strftime("%Y-%m-%dT%H:%M:%S")
        processed_by = random.choice(["cross_sell_agent", "batch_processor", "USR-0042"])
        if random.random() < 0.5:
            enrollment_id = f"ENR-{created.strftime('%Y%m%d')}-{random.randint(1, 999_999):06d}"
        result = {"outcome": random.choice(["enrolled", "skipped", "manual_review"]), "notes": "seeded"}

    window_start = (created - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S")
    window_end = created.strftime("%Y-%m-%dT%H:%M:%S")

    return {
        "signal_id": signal_id,
        "customer_id": customer_id,
        "signal_type": st,
        "severity": sev,
        "score": score,
        "title": title,
        "description": description,
        "events": events,
        "rule_snapshot": rule_snapshot,
        "context": context,
        "suggested_actions": suggested_actions,
        "source": random.choice(["stream_processor", "batch", "manual"]),
        "window_start": window_start,
        "window_end": window_end,
        "processed": processed,
        "processed_at": processed_at,
        "processed_by": processed_by,
        "enrollment_id": enrollment_id,
        "result": result,
        "created_at": created_at,
    }


async def seed_thresholds():
    client = AsyncMongoClient(settings.mongodb_uri)
    db = client[settings.mongodb_db]

    thr_coll = db["thresholds"]
    await thr_coll.drop()
    await thr_coll.insert_many(THRESHOLD_SEEDS)

    sig_coll = db["cross_sell_signals"]
    await sig_coll.drop()
    signals = [_build_signal_doc(i) for i in range(200)]
    await sig_coll.insert_many(signals)

    # Remove legacy collection name if present
    try:
        await db["signal_thresholds"].drop()
    except Exception:
        pass

    print(f"Seeded {len(THRESHOLD_SEEDS)} thresholds and {len(signals)} cross-sell signals")
    await client.close()


if __name__ == "__main__":
    asyncio.run(seed_thresholds())
