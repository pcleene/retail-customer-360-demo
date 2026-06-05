"""Product Insights agent state definition — 9-node LangGraph pipeline."""

from typing import TypedDict


class InsightsState(TypedDict, total=False):
    """State flowing through the 9-node product insights LangGraph pipeline.

    Uses TypedDict (not Pydantic BaseModel) so nodes return partial dicts
    that merge cleanly with LangGraph's state management.
    """

    # Input
    question: str
    role: str  # "internal_staff", supplier ID like "SUP-NESTLE-MY", or partner role
    supplier_id: str  # extracted from role for supplier users

    # Session / user context (for memory-aware responses)
    user_id: str
    session_id: str
    user_preferences: str  # recalled memories injected before the pipeline runs

    # Node 1: inject_rbac
    rbac_filter: dict

    # Node 2: classify_query
    query_type: str  # "aggregation", "search", "comparison", "trend"

    # Node 3: build_aggregation
    mql_pipeline: list[dict]
    collection: str

    # Node 4: run_aggregation
    aggregation_results: list[dict]

    # Node 5: check_realtime
    realtime_kpis: list[dict]
    has_anomaly: bool
    anomaly_message: str

    # Node 6: vector_search_products
    search_results: list[dict]

    # Node 7: rerank_results
    reranked_results: list[dict]

    # Node 8: generate_insights
    insight_analysis: str

    # Node 9: format_response
    formatted_response: str

    # Observability
    queries_executed: list[dict]

    # Error handling
    error: str
