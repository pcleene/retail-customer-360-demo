"""Seed customers into MongoDB with realistic Malaysian data and Voyage AI embeddings.

Embeds all 50K customers (rich embedding_text for vector search). Uses pymongo.AsyncMongoClient.
"""

from __future__ import annotations

import asyncio
import random
from datetime import datetime, timedelta

from pymongo import AsyncMongoClient

from backend.config import settings
from backend.seed.helpers import (
    RetailGroup_STORES,
    CREDIT_PRODUCT_TEMPLATES,
    SEGMENTS,
    SUPPORT_SUBCATEGORIES,
    TIERS,
    TIER_WEIGHTS,
    random_channel_engagement_rates,
    random_date_range,
    random_ic_number,
    random_malaysian_name,
    random_state,
    random_store,
    random_support_note,
    store_geojson,
    stores_in_state,
)
from backend.services.embedding_service import embed_batch

# Build O(1) store name lookup
STORE_BY_ID: dict[str, str] = {s["store_id"]: s["name"] for s in RetailGroup_STORES}

TOTAL_CUSTOMERS = 50_000
EMBED_TOP_K = 50_000
EMBED_BATCH = 128
NOW = datetime(2026, 4, 14)

MARKETING_CHANNELS = ["email", "sms", "push_notification", "in_app", "whatsapp"]

# Per-channel funnel: P(open), P(click|open), P(convert|click)
CHANNEL_FUNNEL: dict[str, tuple[float, float, float]] = {
    "email": (0.25, 0.20, 0.10),
    "sms": (0.45, 0.25, 0.08),
    "push_notification": (0.30, 0.30, 0.12),
    "in_app": (0.55, 0.40, 0.15),
    "whatsapp": (0.60, 0.45, 0.18),
}

SEGMENT_LABELS: dict[str, str] = {
    "retail_only": "retail-only",
    "credit_only": "credit-only",
    "bank_only": "bank-only",
    "retail_credit": "retail-credit",
    "retail_bank": "retail-bank",
    "credit_bank": "credit-bank",
    "tri_entity": "tri-entity",
}

SUPPORT_CHANNELS = [
    "in_store", "mobile_app", "website", "email", "sms", "call_center", "whatsapp",
]


def _entities_from_segment(segment: str) -> list[str]:
    mapping = {
        "retail_only": ["RetailGroup Co"],
        "credit_only": ["RetailGroup Credit"],
        "bank_only": ["RetailGroup Bank"],
        "retail_credit": ["RetailGroup Co", "RetailGroup Credit"],
        "retail_bank": ["RetailGroup Co", "RetailGroup Bank"],
        "credit_bank": ["RetailGroup Credit", "RetailGroup Bank"],
        "tri_entity": ["RetailGroup Co", "RetailGroup Credit", "RetailGroup Bank"],
    }
    return mapping.get(segment, ["RetailGroup Co"])


def _brand_journey(segment: str, join_date: datetime) -> list[dict]:
    milestones = []
    entities_for_seg = {
        "retail_only": ["RetailGroup Co"],
        "credit_only": ["RetailGroup Credit"],
        "bank_only": ["RetailGroup Bank"],
        "retail_credit": ["RetailGroup Co", "RetailGroup Credit"],
        "retail_bank": ["RetailGroup Co", "RetailGroup Bank"],
        "credit_bank": ["RetailGroup Credit", "RetailGroup Bank"],
        "tri_entity": ["RetailGroup Co", "RetailGroup Credit", "RetailGroup Bank"],
    }
    ents = entities_for_seg.get(segment, ["RetailGroup Co"])
    for j, entity in enumerate(ents):
        milestone_date = join_date + timedelta(days=j * random.randint(30, 365))
        if milestone_date > NOW:
            milestone_date = NOW - timedelta(days=random.randint(1, 30))
        milestones.append({"entity": entity, "event": "account_opened", "date": milestone_date.isoformat()})
        for _ in range(random.randint(1, 4)):
            event_type = random.choice([
                "first_purchase", "tier_upgrade", "campaign_enrolled",
                "credit_approved", "loan_disbursed", "card_activated",
                "reward_redeemed", "referral_made",
            ])
            event_date = random_date_range(milestone_date, NOW)
            milestones.append({"entity": entity, "event": event_type, "date": event_date.isoformat()})
    milestones.sort(key=lambda m: m["date"])
    return milestones


def _sample_preferred_stores(state: str, n: int) -> list[dict]:
    candidates = stores_in_state(state)
    if not candidates:
        candidates = RetailGroup_STORES
    physical = [s for s in candidates if not str(s["store_id"]).startswith("ABK-")]
    pool = physical if physical else candidates
    k = min(n, len(pool))
    picks = random.sample(pool, k=k) if k else []
    out = []
    for s in picks:
        out.append({
            "store_id": s["store_id"],
            "visit_count": random.randint(5, 80),
            "avg_basket_at_store_myr": round(random.uniform(30, 500), 2),
            "last_visit": random_date_range(NOW - timedelta(days=120), NOW).strftime("%Y-%m-%d"),
        })
    return out


def _RetailGroup_co_profile(tier: str, join_date: datetime, state: str) -> dict:
    categories = random.sample(
        ["grocery", "electronics", "fashion", "household", "health_beauty"],
        k=random.randint(2, 4),
    )
    pts_amount = random.randint(0, 5000)
    if pts_amount == 0:
        expiry_date = ""
    else:
        exp = NOW + timedelta(days=random.randint(30, 180))
        expiry_date = exp.strftime("%Y-%m-%d")

    last_purchase = random_date_range(NOW - timedelta(days=90), NOW).strftime("%Y-%m-%d")

    return {
        "member_since": join_date.strftime("%Y-%m-%d"),
        "points_balance": random.randint(0, 50000),
        "points_expiring_soon": {"amount": pts_amount, "expiry_date": expiry_date},
        "preferred_stores": _sample_preferred_stores(state, random.randint(1, 3)),
        "top_categories": categories,
        "avg_basket_myr": round(random.uniform(30, 500), 2),
        "visit_frequency_monthly": round(random.uniform(0.5, 12), 1),
        "lifetime_visits": random.randint(20, 500),
        "last_purchase_date": last_purchase,
    }


def _credit_product_row(tmpl: dict, join_date: datetime) -> dict:
    limit = round(random.uniform(*tmpl["limit_range"]), 2)
    outstanding = round(limit * random.uniform(0, 0.85), 2)
    ir_lo, ir_hi = tmpl["interest_rate_range"]
    interest_rate_pct = round(random.uniform(ir_lo, ir_hi), 1)
    tenure_spec = tmpl["tenure_months"]
    if tenure_spec is None:
        tenure_months: int | None = None
        monthly_payment_myr = 0.0
    else:
        lo, hi = tenure_spec
        tenure_months = random.randint(lo, hi)
        monthly_payment_myr = round(outstanding / max(tenure_months, 1), 2)

    issued = random_date_range(join_date, NOW)
    return {
        "product_code": tmpl["product_code"],
        "product_type": tmpl["product_type"],
        "product_name": tmpl["product_name"],
        "issued_date": issued.strftime("%Y-%m-%d"),
        "outstanding_myr": outstanding,
        "limit_myr": limit,
        "utilization_pct": round(outstanding / limit * 100, 1) if limit > 0 else 0.0,
        "monthly_payment_myr": monthly_payment_myr,
        "interest_rate_pct": interest_rate_pct,
        "tenure_months": tenure_months,
        "status": random.choices(["active", "dormant", "closed"], weights=[0.8, 0.15, 0.05], k=1)[0],
    }


def _RetailGroup_credit_profile(join_date: datetime) -> dict:
    num_products = random.randint(1, 3)
    products = [_credit_product_row(random.choice(CREDIT_PRODUCT_TEMPLATES), join_date) for _ in range(num_products)]
    total_limit = sum(p["limit_myr"] for p in products)
    total_outstanding = sum(p["outstanding_myr"] for p in products)
    credit_date = join_date + timedelta(days=random.randint(0, 365))
    if credit_date > NOW:
        credit_date = NOW - timedelta(days=random.randint(1, 30))
    return {
        "member_since": credit_date.strftime("%Y-%m-%d"),
        "products": products,
        "payment_history_score": round(random.uniform(0.5, 1.0), 3),
        "total_credit_limit_myr": round(total_limit, 2),
        "total_outstanding_myr": round(total_outstanding, 2),
    }


def _RetailGroup_bank_profile(join_date: datetime) -> dict:
    bank_date = join_date + timedelta(days=random.randint(30, 730))
    if bank_date > NOW:
        bank_date = NOW - timedelta(days=random.randint(1, 60))
    return {
        "member_since": bank_date.strftime("%Y-%m-%d"),
        "account_type": random.choice(["savings", "current"]),
        "balance_myr": round(random.uniform(100, 100000), 2),
        "has_debit_card": random.random() > 0.3,
        "digital_engagement_score": round(random.uniform(0.2, 1.0), 3),
    }


def _ticket_id(dt: datetime, seq: int) -> str:
    return f"TKT-{dt.year}-{dt.month:02d}-{seq:08d}"


def _agent_id() -> str:
    return f"AGT-{random.randint(1, 200):04d}"


def _support_interactions(join_date: datetime) -> list[dict]:
    n = random.randint(0, 8)
    interactions = []
    for i in range(n):
        idate = random_date_range(max(join_date, NOW - timedelta(days=365)), NOW)
        category = random.choice(list(SUPPORT_SUBCATEGORIES.keys()))
        subcategory = random.choice(SUPPORT_SUBCATEGORIES[category])
        seq = random.randint(1, 99_999_999)
        interactions.append({
            "ticket_id": _ticket_id(idate, seq),
            "date": idate.strftime("%Y-%m-%d"),
            "channel": random.choice(SUPPORT_CHANNELS),
            "agent_id": _agent_id(),
            "category": category,
            "subcategory": subcategory,
            "sentiment": random.choice(["positive", "neutral", "negative"]),
            "resolution": random.choice(["resolved", "escalated", "pending"]),
            "resolution_time_minutes": random.randint(5, 120),
            "notes": random_support_note(category),
        })
    interactions.sort(key=lambda x: x["date"], reverse=True)
    return interactions


def _dt_iso(d: datetime) -> str:
    return d.strftime("%Y-%m-%dT%H:%M:%S")


def _marketing_interactions(
    join_date: datetime,
    campaign_rows: list[dict],
) -> list[dict]:
    n = random.randint(0, 15)
    out = []
    usable = [c for c in campaign_rows if c.get("content_assets")]
    if not usable:
        usable = list(campaign_rows)
    if not usable:
        return out
    for _ in range(n):
        camp = random.choice(usable)
        assets = camp.get("content_assets") or []
        content_id = random.choice(assets) if assets else f"CNT-{random.randint(1, 120):05d}"
        channel = random.choice(MARKETING_CHANNELS)
        p_open, p_click_open, p_conv_click = CHANNEL_FUNNEL[channel]

        sent = random_date_range(max(join_date, NOW - timedelta(days=180)), NOW)
        sent_naive = sent.replace(hour=random.randint(8, 21), minute=random.randint(0, 59), second=random.randint(0, 59))

        opened_at = None
        clicked_at = None
        converted_at = None
        revenue = 0.0

        if random.random() < p_open:
            opened_at = sent_naive + timedelta(minutes=random.randint(1, 180))
            if random.random() < p_click_open:
                clicked_at = opened_at + timedelta(minutes=random.randint(1, 45))
                if random.random() < p_conv_click:
                    converted_at = clicked_at + timedelta(hours=random.randint(1, 72))
                    revenue = round(random.uniform(30, 2000), 2)

        out.append({
            "campaign_id": camp["campaign_id"],
            "content_id": content_id,
            "channel": channel,
            "sent_at": _dt_iso(sent_naive),
            "opened_at": _dt_iso(opened_at) if opened_at else None,
            "clicked_at": _dt_iso(clicked_at) if clicked_at else None,
            "converted_at": _dt_iso(converted_at) if converted_at else None,
            "revenue_attributed_myr": revenue,
        })
    out.sort(key=lambda x: x["sent_at"], reverse=True)
    return out


def _channel_engagement_rates_deep(join_date: datetime) -> dict[str, dict]:
    base = random_channel_engagement_rates()
    for ch in list(base.keys()):
        base[ch]["total_sent"] = random.randint(1, 100)
        le = random_date_range(max(join_date, NOW - timedelta(days=120)), NOW)
        base[ch]["last_engaged_at"] = le.strftime("%Y-%m-%d")
    return base


def _ltv_trend() -> list[dict]:
    base = random.uniform(500, 5000)
    trend = []
    for i in range(12):
        month_dt = NOW - timedelta(days=30 * (11 - i))
        val = base * (1 + random.uniform(-0.1, 0.15))
        base = val
        trend.append({"month": month_dt.strftime("%Y-%m"), "value": round(val, 2)})
    return trend


def _monthly_spend_trend() -> list[dict]:
    base = random.uniform(100, 2000)
    trend = []
    for i in range(12):
        month_dt = NOW - timedelta(days=30 * (11 - i))
        val = base * random.uniform(0.6, 1.5)
        trend.append({"month": month_dt.strftime("%Y-%m"), "value": round(val, 2)})
    return trend


def _ltv_label(ltv: float) -> str:
    if ltv > 50_000:
        return "High-value"
    if ltv > 10_000:
        return "Mid-value"
    return "Value"


def _churn_label(churn: float) -> str:
    if churn < 0.3:
        return "low"
    if churn < 0.6:
        return "medium"
    return "high"


def _top_channels(rates: dict[str, dict], k: int = 2) -> list[str]:
    scored = []
    for name, d in rates.items():
        score = d.get("open_rate", 0) * 0.35 + d.get("ctr", 0) * 0.35 + d.get("conversion_rate", 0) * 0.3
        scored.append((name, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [s[0] for s in scored[:k]]


def _build_embedding_text(
    name: str,
    tier: str,
    segment: str,
    city: str,
    state: str,
    entities: list[str],
    ltv: float,
    cross_sell: float,
    churn: float,
    primary_store_id: str,
    RetailGroup_co: dict | None,
    RetailGroup_credit: dict | None,
    RetailGroup_bank: dict | None,
    rates: dict[str, dict],
    join_date: datetime,
    brand_journey: list[dict],
    comm_prefs: dict,
    ethnicity: str,
    dob_year: int,
) -> str:
    segment_label = SEGMENT_LABELS.get(segment, segment.replace("_", "-"))
    entities_str = ", ".join(entities)
    cats = (RetailGroup_co or {}).get("top_categories") or []
    cat_str = ", ".join(cats) if cats else "general merchandise"

    ps_name = STORE_BY_ID.get(primary_store_id, primary_store_id)
    store_text = f"Primary store {ps_name}"

    pref = (RetailGroup_co or {}).get("preferred_stores") or []
    pref_names = []
    for p in pref[:3]:
        sid = p.get("store_id", "")
        pref_names.append(STORE_BY_ID.get(sid, sid))
    pref_part = ""
    if pref_names:
        pref_part = f" Also shops at {', '.join(pref_names)}."

    tops = _top_channels(rates, 2)
    ch_labels = [c.replace("_", " ") for c in tops]
    channel_text = f"Highest engagement on {' and '.join(ch_labels)}."

    # Credit products held
    credit_parts = []
    if RetailGroup_credit:
        for prod in (RetailGroup_credit.get("products") or [])[:3]:
            pname = prod.get("product_name", "")
            if pname:
                credit_parts.append(pname)
    credit_text = f" Holds {', '.join(credit_parts)}." if credit_parts else ""

    # Bank balance bracket
    bank_text = ""
    if RetailGroup_bank:
        bal = RetailGroup_bank.get("balance_myr", 0)
        if bal > 50000:
            bank_text = f" RetailGroup Bank balance above RM50K."
        elif bal > 10000:
            bank_text = f" RM{bal:,.0f} RetailGroup Bank savings balance."
        elif bal > 0:
            bank_text = f" RetailGroup Bank savings balance under RM10K."

    # Brand journey highlights
    journey_highlights = []
    upgrades = [m for m in brand_journey if m.get("event") == "tier_upgrade"]
    if upgrades:
        last_upgrade = upgrades[-1]
        journey_highlights.append(f"upgraded to {tier} {last_upgrade['date'][:4]}")
    opens = [m for m in brand_journey if m.get("event") == "account_opened"]
    if opens:
        journey_highlights.append(f"joined {opens[0].get('entity', '')} {opens[0]['date'][:4]}")
        if len(opens) > 1:
            journey_highlights.append(f"opened {opens[-1].get('entity', '')} {opens[-1]['date'][:4]}")
    journey_text = f" Journey: {', '.join(journey_highlights)}." if journey_highlights else ""

    # Language and contact preference
    lang = comm_prefs.get("preferred_language", "en")
    lang_map = {"en": "English", "ms": "Bahasa Malaysia", "zh": "Chinese", "ta": "Tamil"}
    pref_time = comm_prefs.get("preferred_contact_time", "evening")
    pref_text = f" Prefers {lang_map.get(lang, lang)}, {pref_time} contact."

    age = NOW.year - dob_year
    demo_text = f" {ethnicity.title()} ethnicity, age {age}."

    return (
        f"{name}, {tier} tier {segment_label} customer in {city}, {state}. "
        f"Active across {entities_str}. {_ltv_label(ltv)}: RM{ltv:,.0f} total LTV, "
        f"cross-sell score {cross_sell:.2f}, {_churn_label(churn)} churn risk {churn:.2f}. "
        f"Top categories {cat_str}. {store_text}.{pref_part} {channel_text}"
        f"{credit_text}{bank_text}{journey_text}{pref_text}{demo_text} "
        f"Joined {join_date.year}."
    )


def _communication_preferences() -> dict:
    return {
        "preferred_language": random.choice(["en", "en", "ms", "ms", "zh", "ta"]),
        "quiet_hours_start": random.choice(["22:00", "22:30", "23:00"]),
        "quiet_hours_end": random.choice(["07:00", "07:30", "08:00"]),
        "preferred_contact_time": random.choice(["morning", "afternoon", "evening"]),
        "do_not_disturb": random.random() < 0.05,
    }


def _signal_id(d: datetime, seq: int) -> str:
    return f"SIG-{d.strftime('%Y%m%d')}-{seq:06d}"


def assign_active_campaigns(customers: list[dict], campaign_rows: list[dict]) -> None:
    """Fill active_campaigns after customer_id reassignment (needs real peer IDs)."""
    usable = [c for c in campaign_rows if c.get("campaign_id")]
    if not usable:
        return

    all_ids = [c["customer_id"] for c in customers]

    for cust in customers:
        if random.random() >= 0.15:
            continue
        n_camps = random.randint(1, 3)
        enrolled_day = random_date_range(
            datetime.strptime(cust["join_date"][:10], "%Y-%m-%d"),
            NOW - timedelta(days=1),
        )
        enrolled_date = enrolled_day.strftime("%Y-%m-%d")
        peer_pool = [x for x in all_ids if x != cust["customer_id"]]

        for _ in range(n_camps):
            camp = random.choice(usable)
            assets = camp.get("content_assets") or []
            content_id = random.choice(assets) if assets else None
            enrolled_by = random.choices(
                ["agent", "manual", "auto_signal"],
                weights=[0.45, 0.25, 0.30],
                k=1,
            )[0]
            sig_id = None
            if enrolled_by == "auto_signal":
                sig_id = _signal_id(enrolled_day, random.randint(1, 999_999))

            similar = (
                random.sample(peer_pool, k=min(5, len(peer_pool)))
                if peer_pool
                else []
            )

            conv_rate = round(random.uniform(0.05, 0.22), 2)
            uplift = round(random.uniform(200, 5000), 2)
            status = "converted" if random.random() < 0.30 else "enrolled"
            converted_at = None
            revenue_r = 0.0
            if status == "converted":
                delta_days = random.randint(1, 60)
                cdt = enrolled_day + timedelta(days=delta_days)
                converted_at = cdt.strftime("%Y-%m-%d")
                revenue_r = round(uplift * random.uniform(0.6, 1.4), 2)

            ch = random.choice(MARKETING_CHANNELS)
            enrollment_seq = random.randint(1, 999_999)
            enrollment_id = f"ENR-{enrolled_day.strftime('%Y%m%d')}-{enrollment_seq:06d}"

            headline = f"{camp['name']} - {ch.replace('_', ' ').title()}"

            cust.setdefault("active_campaigns", []).append({
                "campaign_id": camp["campaign_id"],
                "campaign_name": camp["name"],
                "enrollment_id": enrollment_id,
                "enrolled_date": enrolled_date,
                "enrolled_by": enrolled_by,
                "signal_id": sig_id,
                "content_asset_id": content_id,
                "content_headline": headline,
                "recommended_channel": ch,
                "reasoning": (
                    f"{cust['tier']} customer in {cust['segment'].replace('_', ' ')} segment; "
                    f"expected fit based on engagement and LTV trend."
                ),
                "similar_customer_conversion_rate": conv_rate,
                "expected_ltv_uplift": uplift,
                "similar_customers_sampled": similar,
                "status": status,
                "converted_at": converted_at,
                "revenue_realized_myr": revenue_r,
            })


async def _load_campaign_rows(db) -> list[dict]:
    cur = db["campaigns"].find({}, {"campaign_id": 1, "name": 1, "content_assets": 1})
    rows = await cur.to_list(length=None)
    if rows:
        return rows
    # Fallback when seeding customers standalone (no campaigns in DB)
    return [
        {
            "campaign_id": f"CMP-{i:04d}",
            "name": f"Placeholder Campaign {i}",
            "content_assets": [f"CNT-{((i - 1) * 4 + j + 1):05d}" for j in range(4)],
        }
        for i in range(1, 31)
    ]


def generate_customers(count: int, campaign_rows: list[dict]) -> list[dict]:
    customers = []
    for i in range(count):
        segment = random.choices(SEGMENTS, weights=[0.25, 0.15, 0.10, 0.20, 0.10, 0.08, 0.12], k=1)[0]
        tier = random.choices(TIERS, weights=TIER_WEIGHTS, k=1)[0]
        state = random_state()
        name, ethnicity = random_malaysian_name()
        join_date = random_date_range(datetime(2018, 1, 1), NOW - timedelta(days=30))
        entities = _entities_from_segment(segment)
        primary_store = random_store(state)
        last_visit = random_date_range(NOW - timedelta(days=90), NOW)

        ltv_ranges = {"Basic": (100, 5000), "Silver": (2000, 15000), "Gold": (8000, 50000), "Platinum": (30000, 200000)}
        ltv_min, ltv_max = ltv_ranges[tier]
        ltv = round(random.uniform(ltv_min, ltv_max), 2)

        entity_count = len(entities)
        base_score = random.uniform(0.1, 0.5) + entity_count * 0.15
        cross_sell_score = round(min(base_score + random.uniform(-0.1, 0.2), 1.0), 3)

        churn_risk = round(random.uniform(0.0, 1.0), 3)
        if tier in ("Gold", "Platinum"):
            churn_risk = round(churn_risk * 0.5, 3)

        entity_profiles: dict = {"RetailGroup_co": None, "RetailGroup_credit": None, "RetailGroup_bank": None}
        if "RetailGroup Co" in entities:
            entity_profiles["RetailGroup_co"] = _RetailGroup_co_profile(tier, join_date, state)
        if "RetailGroup Credit" in entities:
            entity_profiles["RetailGroup_credit"] = _RetailGroup_credit_profile(join_date)
        if "RetailGroup Bank" in entities:
            entity_profiles["RetailGroup_bank"] = _RetailGroup_bank_profile(join_date)

        channel_engagement_rates = _channel_engagement_rates_deep(join_date)

        RetailGroup_co = entity_profiles.get("RetailGroup_co")
        comm_prefs = _communication_preferences()
        brand_journey = _brand_journey(segment, join_date)
        dob_year = random.randint(1960, 2000)

        embedding_text = _build_embedding_text(
            name=name,
            tier=tier,
            segment=segment,
            city=primary_store["city"],
            state=state,
            entities=entities,
            ltv=ltv,
            cross_sell=cross_sell_score,
            churn=churn_risk,
            primary_store_id=primary_store["store_id"],
            RetailGroup_co=RetailGroup_co,
            RetailGroup_credit=entity_profiles.get("RetailGroup_credit"),
            RetailGroup_bank=entity_profiles.get("RetailGroup_bank"),
            rates=channel_engagement_rates,
            join_date=join_date,
            brand_journey=brand_journey,
            comm_prefs=comm_prefs,
            ethnicity=ethnicity,
            dob_year=dob_year,
        )

        customer = {
            "customer_id": f"CUST-{i+1:06d}",
            "unified_profile": {
                "name": name,
                "ethnicity": ethnicity,
                "ic_number": random_ic_number(),
                "date_of_birth": f"{dob_year}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
                "gender": random.choice(["male", "female"]),
                "contact": {
                    "email": f"{name.lower().replace(' ', '.').replace('/', '')}@{'gmail.com' if random.random() > 0.3 else 'hotmail.com'}",
                    "phone": f"+60{random.randint(10, 19)}{random.randint(1000000, 9999999)}",
                    "channel_opt_ins": [
                        {"channel": ch, "opted_in": random.random() > 0.2, "opted_in_date": random_date_range(join_date, NOW).isoformat()}
                        for ch in ["email", "sms", "push_notification", "whatsapp"]
                    ],
                    "channel_opt_outs": random.sample(["direct_mail", "telemarketing"], k=random.randint(0, 2)),
                    "communication_preferences": comm_prefs,
                },
                "address": {
                    "street": f"{random.randint(1, 99)} Jalan {random.choice(['Merdeka', 'Sultan', 'Bukit', 'Taman', 'Permai', 'Damai'])} {random.randint(1, 20)}",
                    "city": primary_store["city"],
                    "state": state,
                    "postcode": f"{random.randint(10000, 99999)}",
                    "location": store_geojson(primary_store["store_id"]),
                },
            },
            "segment": segment,
            "tier": tier,
            "entities": entities,
            "entity_profiles": entity_profiles,
            "cross_entity_metrics": {
                "total_ltv": ltv,
                "cross_sell_score": cross_sell_score,
                "churn_risk": churn_risk,
                "ltv_trend": _ltv_trend(),
                "monthly_spend_trend": _monthly_spend_trend(),
            },
            "primary_store_id": primary_store["store_id"],
            "join_date": join_date.strftime("%Y-%m-%d"),
            "last_visit": last_visit.strftime("%Y-%m-%d"),
            "brand_journey": brand_journey,
            "interaction_history": {
                "support_interactions": _support_interactions(join_date),
                "marketing_interactions": _marketing_interactions(join_date, campaign_rows),
                "channel_engagement_rates": channel_engagement_rates,
            },
            "active_campaigns": [],
            "embedding": None,
            "embedding_text": embedding_text,
        }
        customers.append(customer)

        if (i + 1) % 10000 == 0:
            print(f"  Generated {i+1:,}/{count:,} customers")

    return customers


async def seed_customers():
    client = AsyncMongoClient(settings.mongodb_uri)
    db = client[settings.mongodb_db]
    print("Loading campaign metadata for marketing joins...")
    campaign_rows = await _load_campaign_rows(db)

    print(f"Generating {TOTAL_CUSTOMERS:,} customers...")
    customers = generate_customers(TOTAL_CUSTOMERS, campaign_rows)

    customers.sort(key=lambda c: c["cross_entity_metrics"]["total_ltv"], reverse=True)
    for i, c in enumerate(customers):
        c["customer_id"] = f"CUST-{i+1:06d}"

    print("Assigning active campaigns (peer lookalike IDs)...")
    assign_active_campaigns(customers, campaign_rows)

    print(f"Generating embeddings for top {EMBED_TOP_K:,} customers by LTV...")
    top_k = customers[:EMBED_TOP_K]
    texts = [c["embedding_text"] for c in top_k]
    all_embeddings = embed_batch(texts, batch_size=EMBED_BATCH)
    for i, emb in enumerate(all_embeddings):
        top_k[i]["embedding"] = emb
        if (i + 1) % 5000 == 0:
            print(f"  Embedded {i+1:,}/{EMBED_TOP_K:,}")

    print("Inserting into MongoDB...")
    coll = db["customers"]
    await coll.drop()

    batch_size = 2000
    for i in range(0, len(customers), batch_size):
        batch = customers[i : i + batch_size]
        await coll.insert_many(batch)
        if (i + batch_size) % 10000 == 0 or i + batch_size >= len(customers):
            print(f"  Inserted {min(i + batch_size, len(customers)):,}/{TOTAL_CUSTOMERS:,}")

    print(f"Seeded {TOTAL_CUSTOMERS:,} customers ({EMBED_TOP_K:,} with embeddings)")
    await client.close()


if __name__ == "__main__":
    asyncio.run(seed_customers())
