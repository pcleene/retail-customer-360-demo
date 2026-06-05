"""Seed products into MongoDB with Voyage AI embeddings.

Key change: 500K products, only embed top 25K by revenue_ytd.
Full attributes: price_history, inventory, promotions, lifecycle_stage, attributes, tags.
"""

import asyncio
import random
from datetime import datetime, timedelta

from pymongo import AsyncMongoClient

from backend.config import settings
from backend.seed.helpers import (
    RetailGroup_STORES,
    LIFECYCLE_STAGES,
    LIFECYCLE_WEIGHTS,
    PRODUCT_CATEGORIES,
    SUPPLIERS,
    random_product_attributes,
    random_product_tags,
)
from backend.services.embedding_service import embed_batch

BRANDS = {
    "grocery": ["MAGGI", "GARDENIA", "Dutch Lady", "Yeo's", "MAMEE", "Nestle", "Kellogg's",
                 "Ayam Brand", "Jasmine", "Cap Rambutan", "Saji", "Adabi", "Boh", "Milo"],
    "electronics": ["Samsung", "Apple", "Xiaomi", "Oppo", "Vivo", "Sony", "Panasonic",
                     "LG", "Asus", "Huawei", "Dyson", "Daikin"],
    "fashion": ["Uniqlo", "Padini", "Brands Outlet", "Cotton On", "H&M", "Bata",
                 "Hush Puppies", "Vincci", "Carlo Rino", "Skechers"],
    "household": ["Dettol", "Clorox", "Febreze", "Mr. Muscle", "Downy", "Dynamo",
                   "3M", "Lock & Lock", "Akemi", "Cosas United"],
    "health_beauty": ["L'Oreal", "Watsons", "Guardian", "Neutrogena", "Simple", "Nivea",
                       "Eucerin", "Bio-essence", "Laneige", "Innisfree"],
}

TOTAL_PRODUCTS = 500_000
EMBED_TOP_K = 25_000
EMBED_BATCH = 128
NOW = datetime(2026, 4, 13)

# Only retail stores for inventory
RETAIL_STORES = [s for s in RetailGroup_STORES if not s["store_id"].startswith(("ACR-", "ABK-"))]


def _shelf_location(lifecycle: str) -> str:
    if lifecycle == "clearance":
        return f"CLR-{random.randint(1, 9)}"
    aisle_letter = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    aisle_number = random.randint(1, 20)
    shelf_number = random.randint(1, 5)
    return f"{aisle_letter}{aisle_number}-{shelf_number}"


def _safety_stock(category: str) -> int:
    """5–80 units; grocery skews higher."""
    if category == "grocery":
        return random.randint(40, 80)
    if category == "electronics":
        return random.randint(5, 35)
    if category == "fashion":
        return random.randint(8, 40)
    if category == "household":
        return random.randint(10, 45)
    if category == "health_beauty":
        return random.randint(12, 50)
    return random.randint(5, 50)


def _margin_pct(category: str) -> float:
    ranges = {
        "grocery": (5.0, 18.0),
        "electronics": (8.0, 20.0),
        "fashion": (25.0, 45.0),
        "household": (10.0, 25.0),
        "health_beauty": (20.0, 40.0),
    }
    lo, hi = ranges.get(category, (10.0, 25.0))
    return round(random.uniform(lo, hi), 2)


def _return_rate_pct(category: str) -> float:
    if category in ("electronics", "fashion"):
        return round(random.uniform(2.5, 8.0), 2)
    return round(random.uniform(0.5, 4.0), 2)


def _price_history(current_price: float) -> list[dict]:
    """Generate 6-month price history."""
    history = []
    price = current_price * random.uniform(0.9, 1.15)
    for i in range(6):
        month_dt = NOW - timedelta(days=30 * (5 - i))
        price *= random.uniform(0.95, 1.05)
        history.append({"date": month_dt.strftime("%Y-%m-%d"), "price_myr": round(price, 2)})
    return history


def _inventory(category: str, lifecycle: str, num_stores: int = 5) -> dict:
    """Generate inventory across stores with per-store shelf, restock, and supply metrics."""
    stores = random.sample(RETAIL_STORES, k=min(num_stores, len(RETAIL_STORES)))
    by_store = []
    total = 0
    for s in stores:
        units = random.randint(0, 200)
        total += units
        velocity_month = random.uniform(1, 100)
        velocity_day = velocity_month / 30.0
        days_of_supply = round(units / max(velocity_day, 0.1), 2)
        last_dt = NOW - timedelta(days=random.randint(0, 14))
        by_store.append({
            "store_id": s["store_id"],
            "units": units,
            "shelf_location": _shelf_location(lifecycle),
            "last_restock": last_dt.strftime("%Y-%m-%d"),
            "safety_stock": _safety_stock(category),
            "days_of_supply": days_of_supply,
        })
    return {"total_units": total, "by_store": by_store}


def _performance(category: str, price: float) -> dict:
    """Generate performance metrics."""
    cat_multiplier = {"grocery": 5.0, "electronics": 2.0, "fashion": 1.5, "household": 1.8, "health_beauty": 1.3}
    base_units = int(random.uniform(10, 5000) * cat_multiplier.get(category, 1.0))
    revenue = round(base_units * price * random.uniform(0.5, 1.2), 2)

    revenue_last_quarter_myr = round(revenue * 0.25 * random.uniform(0.8, 1.2), 2)
    revenue_yoy_pct = round(random.uniform(-15.0, 30.0), 2)
    margin_pct = _margin_pct(category)
    return_rate_pct = _return_rate_pct(category)

    fbw = []
    for _ in range(random.randint(0, 3)):
        fbw.append({
            "product_id": f"PRD-{random.randint(1, TOTAL_PRODUCTS):07d}",
            "co_purchase_rate": round(random.uniform(0.05, 0.40), 3),
            "lift": round(random.uniform(1.0, 5.0), 3),
        })

    velocity = []
    for s in random.sample(RETAIL_STORES, k=min(3, len(RETAIL_STORES))):
        velocity.append({
            "store_id": s["store_id"],
            "units_per_month": round(random.uniform(1, 100), 1),
        })

    return {
        "revenue_ytd": revenue,
        "units_sold_ytd": base_units,
        "revenue_last_quarter_myr": revenue_last_quarter_myr,
        "revenue_yoy_pct": revenue_yoy_pct,
        "margin_pct": margin_pct,
        "return_rate_pct": return_rate_pct,
        "frequently_bought_with": fbw,
        "velocity_by_store": velocity,
    }


def _promotions() -> dict:
    """Generate promotion data."""
    active = []
    history = []
    if random.random() > 0.7:
        active.append({
            "promo_id": f"PRM-{random.randint(1, 9999):04d}",
            "name": random.choice(["Weekend Sale", "Member Special", "Bundle Deal", "Clearance", "Flash Sale"]),
            "discount_pct": round(random.choice([5, 10, 15, 20, 25, 30, 50]), 0),
            "start_date": (NOW - timedelta(days=random.randint(0, 14))).isoformat(),
            "end_date": (NOW + timedelta(days=random.randint(7, 30))).isoformat(),
            "status": "active",
        })
    for _ in range(random.randint(0, 3)):
        start = NOW - timedelta(days=random.randint(30, 365))
        history.append({
            "promo_id": f"PRM-{random.randint(1, 9999):04d}",
            "name": random.choice(["Hari Raya Sale", "CNY Promo", "Year End", "Back to School", "Deepavali"]),
            "discount_pct": round(random.choice([10, 15, 20, 25, 30]), 0),
            "start_date": start.isoformat(),
            "end_date": (start + timedelta(days=random.randint(7, 30))).isoformat(),
            "status": "completed",
        })
    return {"active_promos": active, "promo_history": history}


def generate_products(count: int) -> list[dict]:
    products = []
    categories = list(PRODUCT_CATEGORIES.keys())
    cat_weights = [0.30, 0.15, 0.15, 0.20, 0.20]

    for i in range(count):
        cat = random.choices(categories, weights=cat_weights, k=1)[0]
        subcategory = random.choice(PRODUCT_CATEGORIES[cat])
        brand = random.choice(BRANDS[cat])
        supplier = random.choice(SUPPLIERS)

        price_ranges = {
            "grocery": (1.50, 80.00),
            "electronics": (29.90, 8999.00),
            "fashion": (19.90, 599.00),
            "household": (3.90, 199.00),
            "health_beauty": (9.90, 399.00),
        }
        min_p, max_p = price_ranges[cat]
        current_price = round(random.uniform(min_p, max_p), 2)
        msrp = round(current_price * random.uniform(1.0, 1.3), 2)

        variant = random.choice(["Standard", "Premium", "Value", "Family", "Mini", "XL", ""])
        name = f"{brand} {subcategory} {variant}".strip()
        lifecycle = random.choices(LIFECYCLE_STAGES, weights=LIFECYCLE_WEIGHTS, k=1)[0]

        attributes = random_product_attributes(cat)
        tags = random_product_tags(cat)

        perf = _performance(cat, current_price)
        hierarchy = [cat, subcategory]
        if variant:
            hierarchy.append(variant.lower())

        tag_str = ", ".join(tags) if tags else ""
        price_tier = "premium" if current_price > 500 else "mid-range" if current_price > 50 else "budget"

        attr_parts = []
        for k, v in attributes.items():
            if isinstance(v, bool):
                if v:
                    attr_parts.append(k.replace("_", " "))
            elif v:
                attr_parts.append(f"{k.replace('_', ' ')}: {v}")
        attr_text = ", ".join(attr_parts[:6])

        inv_stores = [s["store_id"] for s in perf.get("velocity_by_store", [])[:3]]
        inv_text = f"Available in {len(inv_stores)} stores" if inv_stores else ""

        rev = perf.get("revenue_ytd", 0)
        rev_label = "top-seller" if rev > 500000 else "strong revenue" if rev > 100000 else "moderate revenue" if rev > 10000 else "low volume"
        margin = perf.get("margin_pct", 0)
        margin_label = f"{margin:.0f}% margin"

        promo_text = ""
        promos = _promotions()
        active_p = promos.get("active_promos", [])
        if active_p:
            promo_text = f" Currently on {active_p[0]['name']} ({active_p[0]['discount_pct']:.0f}% off)."

        entity = "RetailGroup Co" if cat != "electronics" else random.choice(["RetailGroup Co", "RetailGroup Credit", "RetailGroup Bank"])

        embedding_text = (
            f"{name}, {brand} {subcategory} in {cat} category. {lifecycle} lifecycle, {price_tier} at RM{current_price:,.2f}. "
            f"Supplied by {supplier}. {rev_label} (RM{rev:,.0f} YTD), {margin_label}. "
            f"{attr_text}. {tag_str}. {inv_text}.{promo_text} Sold through {entity}."
        )

        products.append({
            "product_id": f"PRD-{i+1:07d}",
            "name": name,
            "category": cat,
            "subcategory": subcategory,
            "category_hierarchy": hierarchy,
            "brand": brand,
            "supplier_id": supplier,
            "entity": entity,
            "attributes": attributes,
            "tags": tags,
            "price": {
                "current_myr": current_price,
                "msrp_myr": msrp,
                "price_history": _price_history(current_price),
            },
            "inventory": _inventory(cat, lifecycle, num_stores=random.randint(3, 8)),
            "performance": perf,
            "promotions": promos,
            "lifecycle_stage": lifecycle,
            "embedding": None,
            "embedding_text": embedding_text,
        })

        if (i + 1) % 100000 == 0:
            print(f"  Generated {i+1:,}/{count:,} products")

    return products


async def seed_products():
    print(f"Generating {TOTAL_PRODUCTS:,} products...")
    products = generate_products(TOTAL_PRODUCTS)

    # Sort by revenue_ytd descending, embed only top 25K
    products.sort(key=lambda p: p["performance"]["revenue_ytd"], reverse=True)
    # Re-assign IDs after sorting
    for i, p in enumerate(products):
        p["product_id"] = f"PRD-{i+1:07d}"

    print(f"Generating embeddings for top {EMBED_TOP_K:,} products by revenue...")
    top_k = products[:EMBED_TOP_K]
    texts = [p["embedding_text"] for p in top_k]
    all_embeddings = embed_batch(texts, batch_size=EMBED_BATCH)
    for i, emb in enumerate(all_embeddings):
        top_k[i]["embedding"] = emb
        if (i + 1) % 5000 == 0:
            print(f"  Embedded {i+1:,}/{EMBED_TOP_K:,}")

    print(f"  Remaining {TOTAL_PRODUCTS - EMBED_TOP_K:,} products get embedding: null")

    print("Inserting into MongoDB...")
    client = AsyncMongoClient(settings.mongodb_uri)
    db = client[settings.mongodb_db]
    coll = db["products"]
    await coll.drop()

    batch_size = 5000
    for i in range(0, len(products), batch_size):
        batch = products[i : i + batch_size]
        await coll.insert_many(batch)
        if (i + batch_size) % 100000 == 0 or i + batch_size >= len(products):
            print(f"  Inserted {min(i + batch_size, len(products)):,}/{TOTAL_PRODUCTS:,}")

    print(f"Seeded {TOTAL_PRODUCTS:,} products ({EMBED_TOP_K:,} with embeddings)")
    await client.close()


if __name__ == "__main__":
    asyncio.run(seed_products())
