"""Node 1: Classify Intent — determine individual vs. segment mode."""

from backend.agents.crosssell.state import CrossSellState
from backend.agents.crosssell.tracing import traced_node


@traced_node("classify_intent")
async def classify_intent_node(state: CrossSellState) -> dict:
    customer_id = state.get("customer_id", "")
    if customer_id.startswith("CUST-"):
        return {"mode": "individual"}
    return {"mode": "segment"}
