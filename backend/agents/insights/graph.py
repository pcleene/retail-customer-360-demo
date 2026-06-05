"""Product Insights LangGraph pipeline — 9-node sequential pipeline."""

from langgraph.graph import StateGraph, END

from backend.agents.insights.state import InsightsState
from backend.agents.insights.nodes.inject_rbac import inject_rbac_node
from backend.agents.insights.nodes.classify_query import classify_query_node
from backend.agents.insights.nodes.build_aggregation import build_aggregation_node
from backend.agents.insights.nodes.run_aggregation import run_aggregation_node
from backend.agents.insights.nodes.check_realtime import check_realtime_node
from backend.agents.insights.nodes.vector_search_products import vector_search_products_node
from backend.agents.insights.nodes.rerank_results import rerank_results_node
from backend.agents.insights.nodes.generate_insights import generate_insights_node
from backend.agents.insights.nodes.format_response import format_response_node


def build_insights_graph():
    """Build the 9-node product insights agent pipeline.

    Flow:
    inject_rbac -> classify_query -> build_aggregation -> run_aggregation
    -> check_realtime -> vector_search_products -> rerank_results
    -> generate_insights -> format_response -> END
    """
    graph = StateGraph(InsightsState)

    # Add all 9 nodes
    # Note: node names CANNOT match state field names (LangGraph collision)
    graph.add_node("rbac_injection", inject_rbac_node)
    graph.add_node("query_classification", classify_query_node)
    graph.add_node("aggregation_building", build_aggregation_node)
    graph.add_node("aggregation_execution", run_aggregation_node)
    graph.add_node("realtime_check", check_realtime_node)
    graph.add_node("product_vector_search", vector_search_products_node)
    graph.add_node("result_reranking", rerank_results_node)
    graph.add_node("insight_generation", generate_insights_node)
    graph.add_node("response_formatting", format_response_node)

    # Set entry point
    graph.set_entry_point("rbac_injection")

    # Sequential edges: all 9 nodes in order
    graph.add_edge("rbac_injection", "query_classification")
    graph.add_edge("query_classification", "aggregation_building")
    graph.add_edge("aggregation_building", "aggregation_execution")
    graph.add_edge("aggregation_execution", "realtime_check")
    graph.add_edge("realtime_check", "product_vector_search")
    graph.add_edge("product_vector_search", "result_reranking")
    graph.add_edge("result_reranking", "insight_generation")
    graph.add_edge("insight_generation", "response_formatting")
    graph.add_edge("response_formatting", END)

    return graph.compile()


# Singleton compiled graph
insights_agent = build_insights_graph()
