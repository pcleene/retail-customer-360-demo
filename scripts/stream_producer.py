#!/usr/bin/env python3
"""Kafka stream producer — generates synthetic CDC-format events for Retail Customer 360.

Produces to 3 topics:
  - RetailCustomer360.transactions  : POS/online transaction events
  - RetailCustomer360.loyalty_events: Points earn/redeem/expire events
  - RetailCustomer360.profile_changes: Customer profile update events

Usage:
  python -m scripts.stream_producer --bootstrap-servers localhost:9092
  python -m scripts.stream_producer --rate 50 --duration 300
  python -m scripts.stream_producer --burst   # 200 events/sec burst mode
"""

import argparse
import asyncio
import json
import logging
import random
import time
import uuid
from datetime import datetime, timezone

from aiokafka import AIOKafkaProducer

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────

CUSTOMER_ID_RANGE = (1, 50000)
STORE_ID_RANGE = (1, 50)

TOPICS = {
    "transactions": "RetailCustomer360.transactions",
    "loyalty": "RetailCustomer360.loyalty_events",
    "profile": "RetailCustomer360.profile_changes",
}

# Topic weight distribution (70% transactions, 20% loyalty, 10% profile)
TOPIC_WEIGHTS = [0.70, 0.20, 0.10]

PAYMENT_METHODS = [
    "credit_card", "debit_card", "ewallet_tng", "ewallet_boost",
    "ewallet_grabpay", "cash", "qr_pay", "fpx",
]

PRODUCT_CATEGORIES = [
    "groceries", "fresh_produce", "household", "electronics",
    "fashion", "beauty", "sports", "toys", "stationery",
    "beverages", "snacks", "frozen_food", "bakery", "pharmacy",
]

PRODUCT_NAMES = {
    "groceries": ["Rice 5kg", "Cooking Oil 2L", "Sugar 1kg", "Flour 1kg", "Soy Sauce 500ml"],
    "fresh_produce": ["Chicken Breast 1kg", "Salmon Fillet", "Mixed Vegetables", "Banana 1kg", "Watermelon"],
    "household": ["Laundry Detergent 3L", "Dish Soap", "Trash Bags 30pc", "Paper Towels", "Air Freshener"],
    "electronics": ["USB Cable", "Power Bank 10000mAh", "Earbuds", "Phone Case", "Screen Protector"],
    "fashion": ["Cotton T-Shirt", "Denim Jeans", "Sports Shoes", "Backpack", "Sunglasses"],
    "beauty": ["Face Wash", "Moisturiser", "Sunscreen SPF50", "Lip Balm", "Shampoo 500ml"],
    "sports": ["Yoga Mat", "Resistance Band", "Water Bottle 750ml", "Sports Towel", "Skipping Rope"],
    "beverages": ["Mineral Water 1.5L", "Green Tea 500ml", "Coffee 3-in-1", "Milo 1kg", "Fresh Milk 1L"],
    "snacks": ["Potato Chips", "Chocolate Bar", "Mixed Nuts 200g", "Biscuits", "Dried Mango"],
    "frozen_food": ["Frozen Pizza", "Ice Cream 1L", "Frozen Dumplings", "Fish Fingers", "Frozen Peas"],
    "bakery": ["White Bread", "Croissant 4pc", "Butter Cake", "Muffin 6pc", "Baguette"],
    "pharmacy": ["Paracetamol 20pc", "Vitamin C 60pc", "Band-Aid 20pc", "Hand Sanitiser", "Face Mask 50pc"],
    "toys": ["Building Blocks", "Board Game", "Plush Toy", "Puzzle 500pc", "Art Set"],
    "stationery": ["Notebook A5", "Ballpoint Pen 5pc", "Highlighter Set", "Sticky Notes", "Scissors"],
}

LOYALTY_EVENT_TYPES = ["earn", "redeem", "expire"]
TIER_LEVELS = ["bronze", "silver", "gold", "platinum", "diamond"]

PROFILE_FIELDS = [
    "email", "phone", "address_line1", "address_city",
    "address_postcode", "preferred_store", "communication_preference",
    "dietary_preference", "household_size",
]


# ── Event Generators ─────────────────────────────────────────

def _customer_id() -> str:
    idx = random.randint(*CUSTOMER_ID_RANGE)
    return f"CUST-{idx:06d}"


def _store_id() -> str:
    idx = random.randint(*STORE_ID_RANGE)
    return f"STORE-{idx:03d}"


def _generate_items() -> list[dict]:
    """Generate 1-8 line items for a transaction."""
    n_items = random.randint(1, 8)
    items = []
    for _ in range(n_items):
        category = random.choice(PRODUCT_CATEGORIES)
        name = random.choice(PRODUCT_NAMES[category])
        qty = random.randint(1, 5)
        unit_price = round(random.uniform(2.50, 299.90), 2)
        items.append({
            "product_name": name,
            "category": category,
            "quantity": qty,
            "unit_price_myr": unit_price,
            "subtotal_myr": round(qty * unit_price, 2),
        })
    return items


def generate_transaction_event() -> dict:
    """Generate a CDC-format transaction event."""
    items = _generate_items()
    total = round(sum(item["subtotal_myr"] for item in items), 2)
    now = datetime.now(timezone.utc)

    return {
        "operationType": "insert",
        "ns": {"db": "RetailCustomer360", "coll": "transactions"},
        "fullDocument": {
            "transaction_id": f"TXN-{uuid.uuid4().hex[:12].upper()}",
            "customer_id": _customer_id(),
            "store_id": _store_id(),
            "items": items,
            "total_myr": total,
            "payment_method": random.choice(PAYMENT_METHODS),
            "timestamp": now.isoformat(),
            "entity": random.choice(["RetailGroup_RETAIL", "RetailGroup_BIG", "RetailGroup_MAXVALU", "RetailGroup_WELLNESS"]),
        },
        "clusterTime": now.isoformat(),
        "_id": {"_data": uuid.uuid4().hex},
    }


def generate_loyalty_event() -> dict:
    """Generate a CDC-format loyalty event."""
    event_type = random.choice(LOYALTY_EVENT_TYPES)
    customer_id = _customer_id()
    now = datetime.now(timezone.utc)

    points = random.randint(10, 5000) if event_type == "earn" else random.randint(50, 10000)
    if event_type == "expire":
        points = random.randint(100, 2000)

    # 10% chance of tier change on earn events
    tier_change = None
    if event_type == "earn" and random.random() < 0.10:
        old_idx = random.randint(0, len(TIER_LEVELS) - 2)
        tier_change = {
            "old_tier": TIER_LEVELS[old_idx],
            "new_tier": TIER_LEVELS[old_idx + 1],
        }

    doc = {
        "event_id": f"LYL-{uuid.uuid4().hex[:12].upper()}",
        "customer_id": customer_id,
        "event_type": event_type,
        "points": points,
        "balance_after": random.randint(0, 50000),
        "source": random.choice(["purchase", "promotion", "birthday_bonus", "referral"]) if event_type == "earn" else "redemption",
        "timestamp": now.isoformat(),
    }

    if tier_change:
        doc["tier_change"] = tier_change

    return {
        "operationType": "insert",
        "ns": {"db": "RetailCustomer360", "coll": "loyalty_events"},
        "fullDocument": doc,
        "clusterTime": now.isoformat(),
        "_id": {"_data": uuid.uuid4().hex},
    }


def generate_profile_change_event() -> dict:
    """Generate a CDC-format profile change event."""
    field = random.choice(PROFILE_FIELDS)
    now = datetime.now(timezone.utc)

    # Generate plausible old/new values
    old_value, new_value = _generate_field_values(field)

    return {
        "operationType": "update",
        "ns": {"db": "RetailCustomer360", "coll": "customers"},
        "fullDocument": {
            "customer_id": _customer_id(),
            "field_changed": field,
            "old_value": old_value,
            "new_value": new_value,
            "changed_by": random.choice(["customer_app", "call_centre", "admin_portal", "data_sync"]),
            "timestamp": now.isoformat(),
        },
        "clusterTime": now.isoformat(),
        "_id": {"_data": uuid.uuid4().hex},
    }


def _generate_field_values(field: str) -> tuple[str, str]:
    """Generate plausible old/new values for a profile field."""
    if field == "email":
        return "old@example.com", "new@example.com"
    elif field == "phone":
        old = f"+601{random.randint(10000000, 99999999)}"
        new = f"+601{random.randint(10000000, 99999999)}"
        return old, new
    elif field == "address_city":
        cities = ["Kuala Lumpur", "Petaling Jaya", "Shah Alam", "Subang Jaya", "Johor Bahru", "Penang", "Ipoh"]
        old, new = random.sample(cities, 2)
        return old, new
    elif field == "address_postcode":
        return f"{random.randint(10000, 99999)}", f"{random.randint(10000, 99999)}"
    elif field == "preferred_store":
        old_idx, new_idx = random.sample(range(1, 51), 2)
        return f"STORE-{old_idx:03d}", f"STORE-{new_idx:03d}"
    elif field == "communication_preference":
        prefs = ["email", "sms", "push", "whatsapp"]
        old, new = random.sample(prefs, 2)
        return old, new
    elif field == "dietary_preference":
        diets = ["halal", "vegetarian", "none", "vegan", "pescatarian"]
        old, new = random.sample(diets, 2)
        return old, new
    elif field == "household_size":
        return str(random.randint(1, 6)), str(random.randint(1, 8))
    else:
        return "old_value", "new_value"


# ── Event Generators Map ────────────────────────────────────

EVENT_GENERATORS = {
    "transactions": generate_transaction_event,
    "loyalty": generate_loyalty_event,
    "profile": generate_profile_change_event,
}


# ── Producer ────────────────────────────────────────────────

async def produce_events(
    bootstrap_servers: str,
    rate: int,
    duration: int,
):
    """Produce events at the specified rate for the given duration."""
    producer = AIOKafkaProducer(
        bootstrap_servers=bootstrap_servers,
        value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8") if k else None,
        compression_type="gzip",
        linger_ms=10,
        batch_size=32768,
    )

    await producer.start()
    logger.info(
        "Producer started — bootstrap=%s, rate=%d events/sec, duration=%ds",
        bootstrap_servers, rate, duration,
    )

    total_sent = 0
    topic_counts = {"transactions": 0, "loyalty": 0, "profile": 0}
    start_time = time.monotonic()
    interval = 1.0 / rate

    try:
        while (time.monotonic() - start_time) < duration:
            batch_start = time.monotonic()

            # Send a batch of events (1 second worth)
            for _ in range(rate):
                # Choose topic by weight
                topic_key = random.choices(
                    list(EVENT_GENERATORS.keys()),
                    weights=TOPIC_WEIGHTS,
                    k=1,
                )[0]

                event = EVENT_GENERATORS[topic_key]()
                customer_id = event.get("fullDocument", {}).get("customer_id", "unknown")

                await producer.send(
                    TOPICS[topic_key],
                    value=event,
                    key=customer_id,
                )

                total_sent += 1
                topic_counts[topic_key] += 1

            # Log progress every second
            elapsed = time.monotonic() - start_time
            logger.info(
                "Sent %d events (%.0fs elapsed) — txn=%d, loyalty=%d, profile=%d",
                total_sent, elapsed,
                topic_counts["transactions"],
                topic_counts["loyalty"],
                topic_counts["profile"],
            )

            # Sleep for remainder of the 1-second batch interval
            batch_elapsed = time.monotonic() - batch_start
            sleep_time = max(0, 1.0 - batch_elapsed)
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

    except KeyboardInterrupt:
        logger.info("Producer interrupted by user")
    finally:
        await producer.stop()
        elapsed = time.monotonic() - start_time
        actual_rate = total_sent / elapsed if elapsed > 0 else 0
        logger.info(
            "Producer stopped — total=%d events in %.1fs (%.1f events/sec actual)",
            total_sent, elapsed, actual_rate,
        )
        logger.info(
            "Breakdown — transactions=%d, loyalty=%d, profile=%d",
            topic_counts["transactions"],
            topic_counts["loyalty"],
            topic_counts["profile"],
        )


# ── CLI ─────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Retail Customer 360 Kafka stream producer — generates synthetic CDC events",
    )
    parser.add_argument(
        "--bootstrap-servers",
        default=None,
        help="Kafka bootstrap servers (default: from backend.config.settings.kafka_bootstrap_servers)",
    )
    parser.add_argument(
        "--rate",
        type=int,
        default=10,
        help="Events per second (default: 10, range: 1-500)",
    )
    parser.add_argument(
        "--burst",
        action="store_true",
        help="Enable burst mode: 200 events/sec (overrides --rate)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=60,
        help="Duration in seconds (default: 60, 0 = indefinite)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Resolve bootstrap servers
    bootstrap = args.bootstrap_servers
    if not bootstrap:
        try:
            from backend.config import settings
            bootstrap = settings.kafka_bootstrap_servers
        except Exception:
            pass

    if not bootstrap:
        logger.error(
            "No bootstrap servers specified. Use --bootstrap-servers or set KAFKA_BOOTSTRAP_SERVERS in .env"
        )
        raise SystemExit(1)

    rate = 200 if args.burst else args.rate
    rate = max(1, min(rate, 500))  # clamp to sane range

    duration = args.duration if args.duration > 0 else 86400 * 365  # ~indefinite

    logger.info("Mode: %s", "BURST (200/sec)" if args.burst else f"normal ({rate}/sec)")

    asyncio.run(produce_events(bootstrap, rate, duration))


if __name__ == "__main__":
    main()
