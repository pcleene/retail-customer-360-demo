"""Cross-sell LangGraph pipeline — 12-node agent with conditional branching.

Graph topology:
    classify_intent
        ├── [individual] → fetch_profile ─┐
        └── [segment]   → fetch_segment ──┘
                                          ↓
                                   analyze_patterns
                                          ↓
                                vector_search_customers
                                          ↓
                                vector_search_campaigns
                                          ↓
                                 vector_search_content
                                          ↓
                              analyze_similar_conversions
                                          ↓
                                  determine_channel
                                          ↓
                                   rerank_results
                                          ↓
                              generate_recommendations
                                          ↓
                                   execute_actions
                                          ↓
                                         END
"""

from langgraph.graph import StateGraph, END

from backend.agents.crosssell.state import CrossSellState
from backend.agents.crosssell.nodes.n01_classify_intent import classify_intent_node
from backend.agents.crosssell.nodes.n02_fetch_profile import fetch_profile_node
from backend.agents.crosssell.nodes.n03_fetch_segment import fetch_segment_node
from backend.agents.crosssell.nodes.n04_analyze_patterns import analyze_patterns_node
from backend.agents.crosssell.nodes.n05_vector_search_customers import vector_search_customers_node
from backend.agents.crosssell.nodes.n06_vector_search_campaigns import vector_search_campaigns_node
from backend.agents.crosssell.nodes.n07_vector_search_content import vector_search_content_node
from backend.agents.crosssell.nodes.n08_analyze_similar_conversions import analyze_similar_conversions_node
from backend.agents.crosssell.nodes.n09_determine_channel import determine_channel_node
from backend.agents.crosssell.nodes.n10_rerank_results import rerank_results_node
from backend.agents.crosssell.nodes.n11_generate_recommendations import generate_recommendations_node
from backend.agents.crosssell.nodes.n12_execute_actions import execute_actions_node


def _route_by_mode(state: CrossSellState) -> str:
    """Route to fetch_profile (individual) or fetch_segment based on mode."""
    if state.get("error"):
        return END
    if state.get("mode") == "segment":
        return "fetch_segment"
    return "fetch_profile"


def _should_continue(state: CrossSellState) -> str:
    """Continue to the next node unless an error has been set."""
    if state.get("error"):
        return END
    return "continue"


def build_crosssell_graph():
    """Build the 12-node cross-sell agent pipeline with conditional branching."""
    graph = StateGraph(CrossSellState)

    # --- Register all 12 nodes ---
    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("fetch_profile", fetch_profile_node)
    graph.add_node("fetch_segment", fetch_segment_node)
    graph.add_node("analyze_patterns", analyze_patterns_node)
    graph.add_node("vector_search_customers", vector_search_customers_node)
    graph.add_node("vector_search_campaigns", vector_search_campaigns_node)
    graph.add_node("vector_search_content", vector_search_content_node)
    graph.add_node("analyze_similar_conversions", analyze_similar_conversions_node)
    graph.add_node("determine_channel", determine_channel_node)
    graph.add_node("rerank_results", rerank_results_node)
    graph.add_node("generate_recommendations", generate_recommendations_node)
    graph.add_node("execute_actions", execute_actions_node)

    # --- Entry point ---
    graph.set_entry_point("classify_intent")

    # --- Conditional branch: individual vs. segment ---
    graph.add_conditional_edges(
        "classify_intent",
        _route_by_mode,
        {
            "fetch_profile": "fetch_profile",
            "fetch_segment": "fetch_segment",
            END: END,
        },
    )

    # --- Both branches converge into analyze_patterns ---
    graph.add_conditional_edges(
        "fetch_profile",
        _should_continue,
        {"continue": "analyze_patterns", END: END},
    )
    graph.add_conditional_edges(
        "fetch_segment",
        _should_continue,
        {"continue": "analyze_patterns", END: END},
    )

    # --- Linear pipeline from analyze_patterns onward ---
    graph.add_conditional_edges(
        "analyze_patterns",
        _should_continue,
        {"continue": "vector_search_customers", END: END},
    )
    graph.add_conditional_edges(
        "vector_search_customers",
        _should_continue,
        {"continue": "vector_search_campaigns", END: END},
    )
    graph.add_conditional_edges(
        "vector_search_campaigns",
        _should_continue,
        {"continue": "vector_search_content", END: END},
    )
    graph.add_conditional_edges(
        "vector_search_content",
        _should_continue,
        {"continue": "analyze_similar_conversions", END: END},
    )
    graph.add_conditional_edges(
        "analyze_similar_conversions",
        _should_continue,
        {"continue": "determine_channel", END: END},
    )
    graph.add_conditional_edges(
        "determine_channel",
        _should_continue,
        {"continue": "rerank_results", END: END},
    )
    graph.add_conditional_edges(
        "rerank_results",
        _should_continue,
        {"continue": "generate_recommendations", END: END},
    )
    graph.add_conditional_edges(
        "generate_recommendations",
        _should_continue,
        {"continue": "execute_actions", END: END},
    )

    # --- Terminal node ---
    graph.add_edge("execute_actions", END)

    return graph.compile()


# Singleton compiled graph
crosssell_agent = build_crosssell_graph()
