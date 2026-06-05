"""Node 9: Format Response — role-based output formatting."""

import time

from backend.agents.insights.state import InsightsState


async def format_response_node(state: InsightsState) -> dict:
    """Format the insight analysis differently based on the user's role:

    - internal_staff: Full analysis with all data, anomalies, and recommendations
    - supplier (SUP-*): Scoped to their products only, hide competitor data
    - partner roles: High-level summary without granular product details
    """
    t0 = time.time()
    role = state.get("role", "internal_staff")
    insight_analysis = state.get("insight_analysis", "")
    has_anomaly = state.get("has_anomaly", False)
    anomaly_message = state.get("anomaly_message", "")
    aggregation_results = state.get("aggregation_results", [])
    realtime_kpis = state.get("realtime_kpis", [])
    error = state.get("error", "")

    # Handle error state
    if error:
        return {
            "formatted_response": (
                f"**Analysis could not be completed**\n\n"
                f"An error occurred during processing: {error}\n\n"
                f"Please try rephrasing your question or contact support."
            ),
        }

    if role == "internal_staff":
        # Full analysis for internal staff
        sections = []

        sections.append("## Product Insights Analysis\n")
        sections.append(insight_analysis)

        if realtime_kpis:
            sections.append(f"\n\n---\n### Real-time KPI Summary")
            sections.append(f"Monitoring {len(realtime_kpis)} active KPI windows.")
            if has_anomaly:
                sections.append(f"\n**Velocity alert:** {anomaly_message}")

        sections.append(f"\n\n---\n*Data sources: {len(aggregation_results)} aggregation results, "
                        f"{len(realtime_kpis)} real-time KPIs*")

        formatted = "\n".join(sections)

    elif role.startswith("SUP-"):
        # Supplier view — scoped messaging, no competitor data
        supplier_id = state.get("supplier_id", role)
        sections = []

        sections.append(f"## Your Product Performance ({supplier_id})\n")
        sections.append(insight_analysis)

        if has_anomaly:
            sections.append(f"\n\n**Velocity alert:** {anomaly_message}")

        sections.append(
            f"\n\n---\n*This report shows data scoped to your supplier account ({supplier_id}). "
            f"Contact your RetailGroup category manager for broader market context.*"
        )

        formatted = "\n".join(sections)

    elif role.startswith("partner_"):
        # Partner view — high-level summary only
        sections = []

        sections.append("## Market Overview\n")

        # Provide a condensed version of the analysis
        # Truncate the full analysis to key points
        analysis_lines = insight_analysis.split("\n")
        # Keep the first meaningful section (up to ~15 lines)
        condensed_lines = []
        for line in analysis_lines[:15]:
            # Remove overly specific product IDs or supplier references
            condensed_lines.append(line)

        sections.append("\n".join(condensed_lines))

        if len(analysis_lines) > 15:
            sections.append("\n\n*[Additional details available upon request]*")

        sections.append(
            f"\n\n---\n*Summary report prepared for partner access. "
            f"For detailed product-level analytics, please contact RetailGroup directly.*"
        )

        formatted = "\n".join(sections)

    else:
        # Unknown role — minimal response
        formatted = (
            "## Product Insights\n\n"
            f"{insight_analysis}\n\n"
            "---\n*Standard view*"
        )

    view_type = "internal" if role == "internal_staff" else "supplier" if role.startswith("SUP-") else "partner" if role.startswith("partner_") else "standard"

    prev_queries = state.get("queries_executed", [])
    return {
        "formatted_response": formatted,
        "queries_executed": prev_queries + [{
            "node": "format_response",
            "status": "success",
            "duration_ms": round((time.time() - t0) * 1000, 1),
            "view_type": view_type,
            "output_chars": len(formatted),
        }],
    }
