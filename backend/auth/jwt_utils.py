"""JWT utilities for demo RBAC — 4 roles with pre-generated tokens."""

import jwt
from datetime import datetime, timedelta, timezone

JWT_SECRET="<redacted>"
JWT_ALGORITHM = "HS256"

# RBAC filter definitions: what each role can see
ROLE_FILTERS = {
    "internal_staff": {},  # sees everything
    "supplier": lambda supplier_id: {"supplier_id": supplier_id},
    "partner_airline": {"entity": "RetailGroup Credit", "cross_entity_metrics.total_ltv": {"$gte": 10000}},
    "partner_telco": {"entity": {"$in": ["RetailGroup Co", "RetailGroup Bank"]}},
}

# Pre-generated demo tokens (valid for 365 days)
DEMO_USERS = {
    "internal": {
        "user_id": "demo-internal",
        "name": "Sarah Chen",
        "role": "internal_staff",
        "department": "Business Intelligence",
    },
    "supplier_nestle": {
        "user_id": "demo-supplier-nestle",
        "name": "Ahmad Razak",
        "role": "supplier",
        "supplier_id": "SUP-NESTLE-MY",
        "department": "Nestle Malaysia",
    },
    "partner_airline": {
        "user_id": "demo-airline",
        "name": "Mei Ling Wong",
        "role": "partner_airline",
        "department": "Airline Partner",
    },
    "partner_telco": {
        "user_id": "demo-telco",
        "name": "Raj Kumar",
        "role": "partner_telco",
        "department": "Telco Partner",
    },
}


def create_demo_token(user_key: str = "internal") -> str:
    """Create a JWT token for a demo user."""
    user = DEMO_USERS.get(user_key, DEMO_USERS["internal"])
    payload = {
        **user,
        "exp": datetime.now(timezone.utc) + timedelta(days=365),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token."""
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def get_rbac_filter(role: str, supplier_id: str | None = None) -> dict:
    """Get the MongoDB $match filter for a role."""
    if role == "internal_staff":
        return {}
    if role == "supplier" and supplier_id:
        return {"supplier_id": supplier_id}
    filter_def = ROLE_FILTERS.get(role, {})
    if callable(filter_def):
        return filter_def(supplier_id or "")
    return dict(filter_def) if filter_def else {}


# Pre-generate tokens on import
DEMO_TOKENS = {key: create_demo_token(key) for key in DEMO_USERS}
