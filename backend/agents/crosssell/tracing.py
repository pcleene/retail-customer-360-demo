"""Node tracing decorator — captures step-by-step reasoning for the agent."""

import functools
import time
from typing import Callable

from backend.agents.crosssell.state import CrossSellState


def traced_node(node_name: str):
    """Decorator that wraps an async node function to record timing and
    key outputs into ``state["reasoning_steps"]``.
    """

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def wrapper(state: CrossSellState) -> dict:
            t0 = time.perf_counter()
            result = await fn(state)
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)

            step = {
                "step": node_name,
                "duration_ms": elapsed_ms,
            }

            if "error" in result:
                step["status"] = "error"
                step["detail"] = result["error"]
            else:
                step["status"] = "ok"
                detail = _extract_detail(node_name, result)
                if detail:
                    step["detail"] = detail

            reasoning_steps = list(state.get("reasoning_steps", []))
            reasoning_steps.append(step)
            result["reasoning_steps"] = reasoning_steps
            return result

        return wrapper
    return decorator


def _extract_detail(node_name: str, result: dict) -> str | None:
    """Pull a concise summary string from the node output."""
    if node_name == "classify_intent":
        return f"mode={result.get('mode', '?')}"
    if node_name == "fetch_profile":
        p = result.get("customer_profile", {})
        return f"loaded {p.get('unified_profile', {}).get('name', 'profile')}"
    if node_name == "analyze_patterns":
        txt = result.get("pattern_analysis", "")
        return txt[:200] + "..." if len(txt) > 200 else txt
    if node_name == "vector_search_customers":
        return f"{len(result.get('similar_customers', []))} similar customers"
    if node_name == "vector_search_campaigns":
        return f"{len(result.get('matched_campaigns', []))} campaigns matched"
    if node_name == "vector_search_content":
        return f"{len(result.get('matched_content', []))} content assets matched"
    if node_name == "analyze_similar_conversions":
        rate = result.get("similar_conversion_rate")
        return f"conversion_rate={rate}" if rate is not None else None
    if node_name == "determine_channel":
        return f"channel={result.get('optimal_channel', '?')}"
    if node_name == "rerank_results":
        return (f"{len(result.get('reranked_campaigns', []))} campaigns, "
                f"{len(result.get('reranked_content', []))} content reranked")
    if node_name == "generate_recommendations":
        s = result.get("structured_recommendation", {})
        return s.get("reasoning", "")[:200] if s else None
    if node_name == "execute_actions":
        er = result.get("enrollment_result", {})
        return f"enrolled={er.get('enrolled', False)}"
    return None
