"""Node 1: Inject RBAC — set RBAC filter based on user role."""

import time

from backend.agents.insights.state import InsightsState


async def inject_rbac_node(state: InsightsState) -> dict:
    """Read role from state and build the appropriate RBAC filter.

    Roles:
    - "internal_staff": no filter, full access to all data
    - "SUP-*" (supplier ID): filter to only their supplier_id
    - "partner_*": high-level access, filter by entity or category
    """
    t0 = time.time()
    role = state.get("role", "internal_staff")
    rbac_filter: dict = {}
    supplier_id = ""

    if role.startswith("SUP-"):
        supplier_id = role
        rbac_filter = {"supplier_id": supplier_id}

    elif role.startswith("partner_"):
        entity_map = {
            "partner_RetailGroup_co": "RetailGroup Co",
            "partner_RetailGroup_credit": "RetailGroup Credit",
            "partner_RetailGroup_bank": "RetailGroup Bank",
        }
        entity = entity_map.get(role)
        if entity:
            rbac_filter = {"entity": entity}

    access = "full access" if not rbac_filter else f"filtered by {rbac_filter}"

    return {
        "rbac_filter": rbac_filter,
        "supplier_id": supplier_id,
        "queries_executed": [{
            "node": "inject_rbac",
            "status": "success",
            "duration_ms": round((time.time() - t0) * 1000, 1),
            "role": role,
            "filter": rbac_filter,
            "access_level": access,
        }],
    }
