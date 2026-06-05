"""Cross-sell agent state definition — 12-node LangGraph pipeline."""

from typing import TypedDict


class CrossSellState(TypedDict, total=False):
    """State flowing through the 12-node cross-sell LangGraph pipeline."""

    # Input
    customer_id: str

    # Node 1: classify_intent
    mode: str  # "individual" or "segment"

    # Node 2: fetch_profile / Node 3: fetch_segment
    customer_profile: dict
    transactions: list[dict]
    segment_profiles: list[dict]
    segment_query: dict

    # Node 4: analyze_patterns
    pattern_analysis: str

    # Node 5: vector_search_customers
    similar_customers: list[dict]
    similar_customers_sampled: list[str]

    # Node 6: vector_search_campaigns
    matched_campaigns: list[dict]

    # Node 7: vector_search_content
    matched_content: list[dict]

    # Node 8: analyze_similar_conversions
    similar_conversion_analysis: str
    similar_conversion_rate: float

    # Node 9: determine_channel
    optimal_channel: str
    channel_reasoning: str

    # Node 10: rerank_results
    reranked_campaigns: list[dict]
    reranked_content: list[dict]
    targeting_match_score: float
    semantic_similarity: float

    # Node 11: generate_recommendations
    recommendation: str
    structured_recommendation: dict
    expected_ltv_uplift: float

    # Node 12: execute_actions
    enrollment_result: dict
    enrolled: bool

    # Observability
    queries_executed: list[dict]
    reasoning_steps: list[dict]

    # Error handling
    error: str
