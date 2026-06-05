"""Node 9: Determine Channel — pick optimal delivery channel from engagement data."""

from backend.agents.crosssell.state import CrossSellState
from backend.agents.crosssell.tracing import traced_node


@traced_node("determine_channel")
async def determine_channel_node(state: CrossSellState) -> dict:
    profile = state.get("customer_profile", {})
    interaction_history = profile.get("interaction_history", {})
    channel_rates = interaction_history.get("channel_engagement_rates", {})

    if not channel_rates:
        return {
            "optimal_channel": "email",
            "channel_reasoning": (
                "No channel engagement data available for this customer. "
                "Defaulting to email as the safest broad-reach channel."
            ),
        }

    best_channel = None
    best_rate = -1.0
    reasoning_parts = []

    for channel, metrics in channel_rates.items():
        if isinstance(metrics, dict):
            conversion_rate = metrics.get("conversion_rate", 0)
            sent = metrics.get("total_sent", metrics.get("sent", 0))
            converted = int(sent * conversion_rate) if sent else 0
        else:
            conversion_rate = 0
            sent = 0
            converted = 0

        reasoning_parts.append(
            f"  - {channel}: {conversion_rate:.1%} conversion "
            f"({converted}/{sent} sent)"
        )

        if conversion_rate > best_rate:
            best_rate = conversion_rate
            best_channel = channel

    channel_reasoning = (
        f"Selected '{best_channel}' based on highest conversion rate "
        f"({best_rate:.1%}) from customer's engagement history:\n"
        + "\n".join(sorted(reasoning_parts, reverse=True))
    )

    return {
        "optimal_channel": best_channel,
        "channel_reasoning": channel_reasoning,
    }
