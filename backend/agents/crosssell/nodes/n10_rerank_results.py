"""Node 10: Rerank Results — Voyage rerank-2.5 on campaigns + content."""

from backend.agents.crosssell.state import CrossSellState
from backend.agents.crosssell.tracing import traced_node
from backend.services.embedding_service import rerank


@traced_node("rerank_results")
async def rerank_results_node(state: CrossSellState) -> dict:
    queries_executed = list(state.get("queries_executed", []))
    pattern_analysis = state.get("pattern_analysis", "")
    matched_campaigns = state.get("matched_campaigns", [])
    matched_content = state.get("matched_content", [])

    reranked_campaigns = list(matched_campaigns)
    reranked_content = list(matched_content)
    targeting_match_score = 0.0
    semantic_similarity = 0.0

    if matched_campaigns and pattern_analysis:
        campaign_docs = [
            f"{c.get('name', '')} — {c.get('description', '')} "
            f"(entity: {c.get('entity', '')}, type: {c.get('type', '')})"
            for c in matched_campaigns
        ]

        campaign_rerank = rerank(
            query=pattern_analysis[:1000],
            documents=campaign_docs,
            top_k=min(len(campaign_docs), 10),
        )

        reranked_campaigns = []
        for r in campaign_rerank:
            idx = r["index"]
            campaign = dict(matched_campaigns[idx])
            campaign["rerank_score"] = r["relevance_score"]
            reranked_campaigns.append(campaign)

        if reranked_campaigns:
            targeting_match_score = reranked_campaigns[0].get("rerank_score", 0)

        queries_executed.append({
            "node": "rerank_results",
            "operation": "rerank (campaigns)",
            "model": "rerank-2.5",
            "documents_count": len(campaign_docs),
            "top_k": len(campaign_rerank),
        })

    if matched_content and pattern_analysis:
        content_docs = [
            f"{c.get('headline', '')} — {c.get('body_preview', c.get('description', ''))} "
            f"(channel: {c.get('channel', '')}, persona: {c.get('target_persona', '')})"
            for c in matched_content
        ]

        content_rerank = rerank(
            query=pattern_analysis[:1000],
            documents=content_docs,
            top_k=min(len(content_docs), 10),
        )

        reranked_content = []
        for r in content_rerank:
            idx = r["index"]
            content = dict(matched_content[idx])
            content["rerank_score"] = r["relevance_score"]
            reranked_content.append(content)

        if reranked_content:
            semantic_similarity = reranked_content[0].get("rerank_score", 0)

        queries_executed.append({
            "node": "rerank_results",
            "operation": "rerank (content)",
            "model": "rerank-2.5",
            "documents_count": len(content_docs),
            "top_k": len(content_rerank),
        })

    return {
        "reranked_campaigns": reranked_campaigns,
        "reranked_content": reranked_content,
        "targeting_match_score": targeting_match_score,
        "semantic_similarity": semantic_similarity,
        "queries_executed": queries_executed,
    }
