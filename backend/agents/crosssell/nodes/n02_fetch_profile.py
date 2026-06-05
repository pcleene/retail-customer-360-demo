"""Node 2: Fetch Profile — load full customer profile + recent transactions."""

from backend.agents.crosssell.state import CrossSellState
from backend.agents.crosssell.tracing import traced_node
from backend.database import get_db


@traced_node("fetch_profile")
async def fetch_profile_node(state: CrossSellState) -> dict:
    db = get_db()
    customer_id = state["customer_id"]
    queries_executed = list(state.get("queries_executed", []))

    customer_query = {"customer_id": customer_id}
    customer_projection = {"_id": 0, "embedding": 0}

    profile = await db["customers"].find_one(customer_query, customer_projection)

    queries_executed.append({
        "node": "fetch_profile",
        "collection": "customers",
        "operation": "find_one",
        "query": customer_query,
        "projection": customer_projection,
    })

    if not profile:
        return {
            "error": f"Customer {customer_id} not found",
            "queries_executed": queries_executed,
        }

    txn_pipeline = [
        {"$match": {"customer_id": customer_id}},
        {"$sort": {"transaction_date": -1}},
        {"$limit": 50},
        {"$project": {"_id": 0, "embedding": 0}},
    ]

    transactions = []
    async for doc in await db["transactions"].aggregate(txn_pipeline):
        transactions.append(doc)

    queries_executed.append({
        "node": "fetch_profile",
        "collection": "transactions",
        "operation": "aggregate",
        "pipeline": txn_pipeline,
    })

    return {
        "customer_profile": profile,
        "transactions": transactions,
        "queries_executed": queries_executed,
    }
