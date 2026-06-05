"""Seed transactions into MongoDB - 2M transactions over 18 months."""

import asyncio
import random
from datetime import datetime, timedelta

from pymongo import AsyncMongoClient

from backend.config import settings
from backend.seed.helpers import RetailGroup_STORES, PRODUCT_CATEGORIES

TOTAL_TRANSACTIONS = 2_000_000
TOTAL_CUSTOMERS = 50_000
NOW = datetime(2026, 4, 13)
START = NOW - timedelta(days=540)  # 18 months

# Seasonal multipliers by month (1=Jan..12=Dec)
SEASONAL = {
    1: 1.3,
    2: 1.5,
    3: 0.9,
    4: 0.9,
    5: 1.1,
    6: 1.0,
    7: 0.9,
    8: 0.9,
    9: 1.0,
    10: 1.0,
    11: 1.2,
    12: 1.4,
}

PAYMENT_METHODS = ["cash", "debit_card", "credit_card", "ewallet", "RetailGroup_card", "RetailGroup_bank"]
CATEGORIES = list(PRODUCT_CATEGORIES.keys())

# Align with seed_products / DATA_MODEL canonical samples
BRANDS = {
    "grocery": [
        "MAGGI",
        "GARDENIA",
        "Dutch Lady",
        "Yeo's",
        "MAMEE",
        "Nestle",
        "Kellogg's",
        "Ayam Brand",
        "Jasmine",
        "Cap Rambutan",
        "Saji",
        "Adabi",
        "Boh",
        "Milo",
    ],
    "electronics": [
        "Samsung",
        "Apple",
        "Xiaomi",
        "Oppo",
        "Vivo",
        "Sony",
        "Panasonic",
        "LG",
        "Asus",
        "Huawei",
        "Dyson",
        "Daikin",
    ],
    "fashion": [
        "Uniqlo",
        "Padini",
        "Brands Outlet",
        "Cotton On",
        "H&M",
        "Bata",
        "Hush Puppies",
        "Vincci",
        "Carlo Rino",
        "Skechers",
    ],
    "household": [
        "Dettol",
        "Clorox",
        "Febreze",
        "Mr. Muscle",
        "Downy",
        "Dynamo",
        "3M",
        "Lock & Lock",
        "Akemi",
        "Cosas United",
    ],
    "health_beauty": [
        "L'Oreal",
        "Watsons",
        "Guardian",
        "Neutrogena",
        "Simple",
        "Nivea",
        "Eucerin",
        "Bio-essence",
        "Laneige",
        "Innisfree",
    ],
}

TIER_MULTIPLIER = {"Basic": 1.0, "Silver": 1.5, "Gold": 2.0, "Platinum": 3.0}

DISCOUNT_TYPES = ["promo", "member_discount", "voucher", "points_redemption", "tier_discount"]

_DISCOUNT_CODE_DESC = {
    "promo": [
        ("MEMBER8", "Member Special 8% on tagged items"),
        ("RAYA25", "Hari Raya seasonal markdown"),
        ("FLASH10", "Flash deal 10% off basket"),
    ],
    "member_discount": [
        ("MEMSAVE", "Member price discount"),
        ("RetailGroupPLUS", "RetailGroup Plus member savings"),
    ],
    "voucher": [
        ("VOUCH50", "RM50 welcome voucher"),
        ("APP20", "App-exclusive RM20 off"),
    ],
    "points_redemption": [
        ("PTS2CASH", "Points redemption offset"),
        ("LOY1000", "1,000 points redeemed at checkout"),
    ],
    "tier_discount": [
        ("PLAT-50", "Platinum tier RM50 instant rebate"),
        ("GOLD-20", "Gold tier RM20 instant rebate"),
        ("SILV-10", "Silver tier RM10 instant rebate"),
    ],
}


def _tier_for_customer(customer_idx: int) -> str:
    """Tier by customer index — matches 60/25/12/3 split over 50K customers."""
    if customer_idx <= 1500:
        return "Platinum"
    if customer_idx <= 7500:
        return "Gold"
    if customer_idx <= 20000:
        return "Silver"
    return "Basic"


def _pick_channel() -> str:
    r = random.random()
    if r < 0.65:
        return "in_store"
    if r < 0.85:
        return "online"
    return "mobile_app"


def _seasonal_date() -> datetime:
    """Generate a date with seasonal weighting."""
    days_range = (NOW - START).days
    day_offset = random.randint(0, days_range)
    candidate = START + timedelta(days=day_offset)
    month_weight = SEASONAL.get(candidate.month, 1.0)
    if random.random() < month_weight / 1.5:
        return candidate
    return candidate


def _random_time_on_date(d: datetime) -> datetime:
    return d.replace(
        hour=random.randint(0, 23),
        minute=random.randint(0, 59),
        second=random.randint(0, 59),
        microsecond=random.randint(0, 999999),
    )


def _build_payment(method: str, tx_date: datetime, total_myr: float) -> dict:
    card_last4 = None
    if method in ("credit_card", "debit_card", "RetailGroup_card"):
        card_last4 = f"{random.randint(1000, 9999)}"
    installment_months = None
    if method == "RetailGroup_card" and total_myr > 500 and random.random() < 0.3:
        installment_months = random.choice([3, 6, 12])
    auth_code = f"AUTH-{tx_date.strftime('%Y-%m')}-{random.randint(100000, 999999)}"
    return {
        "method": method,
        "card_last4": card_last4,
        "RetailGroup_card_used": method in ("RetailGroup_card", "RetailGroup_bank"),
        "installment_months": installment_months,
        "auth_code": auth_code,
    }


def _document_discounts(subtotal_myr: float, tier: str) -> tuple[list[dict], float]:
    """~30% of callers should pass has_discounts gate before calling."""
    n = random.randint(1, 2)
    discounts = []
    total_pct = 0.0
    for _ in range(n):
        dtype = random.choice(DISCOUNT_TYPES)
        pct = random.uniform(0.05, 0.30)
        # avoid extreme stack
        if total_pct + pct > 0.55:
            pct = max(0.05, min(0.30, 0.55 - total_pct))
        if pct <= 0:
            break
        total_pct += pct
        amount = round(subtotal_myr * pct, 2)
        code, desc = random.choice(_DISCOUNT_CODE_DESC[dtype])
        if dtype == "tier_discount":
            if tier == "Platinum":
                code, desc = _DISCOUNT_CODE_DESC["tier_discount"][0]
            elif tier == "Gold":
                code, desc = _DISCOUNT_CODE_DESC["tier_discount"][1]
            else:
                code, desc = _DISCOUNT_CODE_DESC["tier_discount"][2]
        discounts.append(
            {
                "type": dtype,
                "amount_myr": amount,
                "code": code,
                "description": desc,
            }
        )
    total_discount = round(sum(d["amount_myr"] for d in discounts), 2)
    return discounts, total_discount


def generate_transactions(count: int) -> list[dict]:
    transactions = []
    stores = RetailGroup_STORES
    retail_stores = [s for s in stores if not s["store_id"].startswith(("ACR-", "ABK-"))]

    price_ranges = {
        "grocery": (1.50, 45.00),
        "electronics": (49.90, 4999.00),
        "fashion": (19.90, 299.00),
        "household": (5.90, 99.00),
        "health_beauty": (12.90, 199.00),
    }

    for i in range(count):
        customer_idx = random.randint(1, TOTAL_CUSTOMERS)
        customer_id = f"CUST-{customer_idx:06d}"
        tier = _tier_for_customer(customer_idx)
        tier_mult = TIER_MULTIPLIER[tier]

        tx_day = _seasonal_date()
        tx_date = _random_time_on_date(tx_day)

        channel = _pick_channel()
        store = random.choice(retail_stores)

        num_items = random.choices(
            [1, 2, 3, 4, 5, 6, 7, 8],
            weights=[0.15, 0.25, 0.25, 0.15, 0.10, 0.05, 0.03, 0.02],
            k=1,
        )[0]

        items_raw = []
        subtotal_myr = 0.0

        for _ in range(num_items):
            cat = random.choices(CATEGORIES, weights=[0.35, 0.10, 0.15, 0.20, 0.20], k=1)[0]
            subcategory = random.choice(PRODUCT_CATEGORIES[cat])
            brand = random.choice(BRANDS[cat])
            name = f"{brand} {subcategory}"
            qty = random.randint(1, 5) if cat == "grocery" else 1
            min_p, max_p = price_ranges[cat]
            unit_price = round(random.uniform(min_p, max_p), 2)
            gross = round(unit_price * qty, 2)
            subtotal_myr += gross

            # Item-level promo / discount (not all lines)
            promo_id = None
            discount_per_unit = 0.0
            if random.random() < 0.25:
                promo_id = f"PRM-{random.randint(1000, 9999)}"
                discount_per_unit = round(unit_price * random.uniform(0.02, 0.12), 2)
                discount_per_unit = min(discount_per_unit, unit_price * 0.5)

            line_total = round((unit_price - discount_per_unit) * qty, 2)
            product_idx = random.randint(1, 500000)
            items_raw.append(
                {
                    "product_id": f"PRD-{product_idx:07d}",
                    "name": name,
                    "category": cat,
                    "subcategory": subcategory,
                    "brand": brand,
                    "quantity": qty,
                    "unit_price": unit_price,
                    "discount_per_unit": discount_per_unit,
                    "line_total": line_total,
                    "promo_id": promo_id,
                    "_line_net": line_total,
                }
            )

        subtotal_myr = round(subtotal_myr, 2)
        sum_line_net = round(sum(x["_line_net"] for x in items_raw), 2)

        has_doc_discounts = random.random() < 0.30
        if has_doc_discounts:
            discounts, total_discount_myr = _document_discounts(subtotal_myr, tier)
        else:
            discounts, total_discount_myr = [], 0.0

        if sum_line_net <= 0:
            discounts, total_discount_myr = [], 0.0
        elif total_discount_myr > sum_line_net and discounts:
            scale = sum_line_net / total_discount_myr
            for d in discounts:
                d["amount_myr"] = round(d["amount_myr"] * scale, 2)
            total_discount_myr = round(sum(d["amount_myr"] for d in discounts), 2)
        total_myr = round(max(0.0, sum_line_net - total_discount_myr), 2)

        bonus_multiplier = 2.0 if random.random() < 0.05 else 1.0
        points = int(total_myr * tier_mult * bonus_multiplier)

        # Allocate item loyalty points proportional to line net
        if sum_line_net > 0 and points > 0:
            allocated = 0
            for j, it in enumerate(items_raw):
                if j == len(items_raw) - 1:
                    it["loyalty_points_earned"] = max(0, points - allocated)
                else:
                    pts = int(points * (it["_line_net"] / sum_line_net))
                    allocated += pts
                    it["loyalty_points_earned"] = pts
        else:
            for it in items_raw:
                it["loyalty_points_earned"] = 0

        for it in items_raw:
            del it["_line_net"]

        method = random.choice(PAYMENT_METHODS)
        payment = _build_payment(method, tx_date, total_myr)

        points_redeemed = random.randint(0, 500) if random.random() < 0.1 else 0
        loyalty = {
            "points_earned": points,
            "points_redeemed": points_redeemed,
            "tier_at_purchase": tier,
            "member_id": customer_id,
            "bonus_multiplier": bonus_multiplier,
        }

        campaign_attribution = f"CMP-{random.randint(1, 30):04d}" if random.random() < 0.05 else None
        is_returned = random.random() < 0.015

        transactions.append(
            {
                "transaction_id": f"TXN-{i + 1:08d}",
                "customer_id": customer_id,
                "store_id": store["store_id"],
                "date": tx_date.isoformat(),
                "channel": channel,
                "items": items_raw,
                "subtotal_myr": subtotal_myr,
                "discounts": discounts,
                "total_discount_myr": total_discount_myr,
                "total_myr": total_myr,
                "payment": payment,
                "loyalty": loyalty,
                "entity": "RetailGroup Co",
                "campaign_attribution": campaign_attribution,
                "is_returned": is_returned,
            }
        )

        if (i + 1) % 200000 == 0:
            print(f"  Generated {i + 1:,}/{count:,} transactions")

    return transactions


async def seed_transactions():
    print(f"Generating {TOTAL_TRANSACTIONS:,} transactions...")
    transactions = generate_transactions(TOTAL_TRANSACTIONS)

    print("Inserting into MongoDB...")
    client = AsyncMongoClient(settings.mongodb_uri)
    db = client[settings.mongodb_db]
    coll = db["transactions"]
    await coll.drop()

    batch_size = 10000
    for i in range(0, len(transactions), batch_size):
        batch = transactions[i : i + batch_size]
        await coll.insert_many(batch)
        if (i + batch_size) % 200000 == 0 or i + batch_size >= len(transactions):
            print(f"  Inserted {min(i + batch_size, len(transactions)):,}/{TOTAL_TRANSACTIONS:,}")

    print(f"Seeded {TOTAL_TRANSACTIONS:,} transactions")
    await client.close()


if __name__ == "__main__":
    asyncio.run(seed_transactions())
