"""Seed RetailGroup stores into MongoDB with GeoJSON locations."""

import asyncio
import random

from pymongo import AsyncMongoClient

from backend.config import settings
from backend.seed.helpers import RetailGroup_STORES, ANCHOR_TENANTS, STORE_COORDINATES, STORE_SERVICES


def _standard_opening_hours() -> dict[str, str]:
    return {
        "monday": "10:00-22:00",
        "tuesday": "10:00-22:00",
        "wednesday": "10:00-22:00",
        "thursday": "10:00-22:00",
        "friday": "10:00-22:30",
        "saturday": "10:00-22:30",
        "sunday": "10:00-22:00",
    }


def _digital_opening_hours() -> dict[str, str]:
    h = "00:00-24:00"
    return {d: h for d in ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")}


def _store_format(store_id: str) -> str:
    if store_id.startswith("RetailGroup-"):
        return "mall"
    if store_id.startswith("MXV-"):
        return "standalone"
    if store_id.startswith("BIG-"):
        return "hypermart"
    if store_id.startswith("ACR-"):
        return "branch"
    if store_id.startswith("ABK-"):
        return "kiosk" if store_id in ("ABK-KIO", "ABK-PRT") else "digital"
    return "other"


def _store_brand(store_id: str) -> str:
    if store_id.startswith("RetailGroup-"):
        return "RetailGroup"
    if store_id.startswith("MXV-"):
        return "MaxValu"
    if store_id.startswith("BIG-"):
        return "RetailGroup BiG"
    if store_id.startswith("ACR-"):
        return "RetailGroup Credit"
    if store_id.startswith("ABK-"):
        return "RetailGroup Bank"
    return "RetailGroup"


BANK_DIGITAL_SERVICES = ["account_opening", "fund_transfer", "fixed_deposit", "loan_application"]


def _store_operating_context(store_id: str, fmt: str) -> tuple[dict[str, str], list[str], int, int, bool, bool, list[str]]:
    """opening_hours, anchor_tenants, parking_bays, avg_daily_footfall, has_drive_thru, has_food_court, services_offered."""
    if store_id.startswith("ABK-") and store_id in ("ABK-DIG", "ABK-APP", "ABK-WEB"):
        return (
            _digital_opening_hours(),
            [],
            0,
            0,
            False,
            False,
            BANK_DIGITAL_SERVICES,
        )
    if store_id.startswith("ABK-") and store_id in ("ABK-KIO", "ABK-PRT"):
        oh = _standard_opening_hours()
        return (
            oh,
            [],
            random.randint(0, 5),
            random.randint(80, 500),
            False,
            False,
            BANK_DIGITAL_SERVICES,
        )
    if fmt == "digital":
        return (
            _digital_opening_hours(),
            [],
            0,
            0,
            False,
            False,
            BANK_DIGITAL_SERVICES,
        )
    if fmt == "kiosk":
        oh = _standard_opening_hours()
        anchors: list[str] = []
        parking = random.randint(0, 5)
        footfall = random.randint(80, 500)
        drive = random.random() < 0.10
        food = False
        services = random.sample(
            STORE_SERVICES,
            k=random.randint(2, min(5, len(STORE_SERVICES))),
        )
        return (oh, anchors, parking, footfall, drive, food, services)
    if fmt == "branch":
        oh = _standard_opening_hours()
        anchors = []
        parking = random.randint(20, 120)
        footfall = random.randint(150, 1200)
        drive = random.random() < 0.10
        food = False
        services = random.sample(
            STORE_SERVICES,
            k=random.randint(2, min(5, len(STORE_SERVICES))),
        )
        return (oh, anchors, parking, footfall, drive, food, services)
    if fmt == "mall":
        oh = _standard_opening_hours()
        anchors = random.sample(ANCHOR_TENANTS, k=random.randint(2, 5))
        parking = random.randint(500, 2000)
        footfall = random.randint(2000, 8000)
        drive = random.random() < 0.10
        food = True
        services = random.sample(
            STORE_SERVICES,
            k=random.randint(2, min(5, len(STORE_SERVICES))),
        )
        return (oh, anchors, parking, footfall, drive, food, services)
    if fmt == "hypermart":
        oh = _standard_opening_hours()
        anchors = random.sample(ANCHOR_TENANTS, k=random.randint(2, 5))
        parking = random.randint(200, 800)
        footfall = random.randint(800, 3000)
        drive = random.random() < 0.10
        food = True
        services = random.sample(
            STORE_SERVICES,
            k=random.randint(2, min(5, len(STORE_SERVICES))),
        )
        return (oh, anchors, parking, footfall, drive, food, services)
    # standalone (MXV — no anchor tenants per spec; only mall/hypermart have anchors)
    oh = _standard_opening_hours()
    anchors: list[str] = []
    parking = random.randint(200, 800)
    footfall = random.randint(800, 3000)
    drive = random.random() < 0.10
    food = False
    services = random.sample(
        STORE_SERVICES,
        k=random.randint(2, min(5, len(STORE_SERVICES))),
    )
    return (oh, anchors, parking, footfall, drive, food, services)


async def seed_stores():
    stores = []
    for s in RetailGroup_STORES:
        coords = STORE_COORDINATES.get(s["store_id"])
        location = {"type": "Point", "coordinates": coords} if coords else None
        fmt = _store_format(s["store_id"])
        (
            opening_hours,
            anchor_tenants,
            parking_bays,
            avg_daily_footfall,
            has_drive_thru,
            has_food_court,
            services_offered,
        ) = _store_operating_context(s["store_id"], fmt)

        stores.append({
            "store_id": s["store_id"],
            "name": s["name"],
            "brand": _store_brand(s["store_id"]),
            "state": s["state"],
            "city": s["city"],
            "address": f"Lot {random.randint(1, 999)}, {s['city']}, {s['state']}",
            "location": location,
            "format": fmt,
            "opening_date": f"{random.randint(2000, 2024)}-01-01",
            "size_sqm": random.randint(500, 15000) if fmt not in ("digital",) else 0,
            "opening_hours": opening_hours,
            "anchor_tenants": anchor_tenants,
            "parking_bays": parking_bays,
            "avg_daily_footfall": avg_daily_footfall,
            "has_drive_thru": has_drive_thru,
            "has_food_court": has_food_court,
            "services_offered": services_offered,
        })

    client = AsyncMongoClient(settings.mongodb_uri)
    db = client[settings.mongodb_db]
    coll = db["stores"]
    await coll.drop()
    if stores:
        await coll.insert_many(stores)
    print(f"Seeded {len(stores)} stores with GeoJSON locations")
    await client.close()


if __name__ == "__main__":
    asyncio.run(seed_stores())
