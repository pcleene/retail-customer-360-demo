import voyageai

from backend.config import settings

_client: voyageai.Client | None = None


def _get_client() -> voyageai.Client:
    global _client
    if _client is None:
        _client = voyageai.Client(api_key=settings.voyage_api_key)
    return _client


def embed_for_index(texts: list[str], input_type: str = "document") -> list[list[float]]:
    """Embed texts for indexing using voyage-4-large."""
    client = _get_client()
    result = client.embed(
        texts,
        model=settings.voyage_index_model,
        input_type=input_type,
    )
    return result.embeddings


def embed_for_query(text: str) -> list[float]:
    """Embed a single query text using voyage-4-lite (shared space with voyage-4-large)."""
    client = _get_client()
    result = client.embed(
        [text],
        model=settings.voyage_query_model,
        input_type="query",
    )
    return result.embeddings[0]


def embed_batch(texts: list[str], batch_size: int = 128, input_type: str = "document") -> list[list[float]]:
    """Embed large batches by splitting into chunks."""
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        embeddings = embed_for_index(batch, input_type=input_type)
        all_embeddings.extend(embeddings)
        if (i + batch_size) % 1000 == 0:
            print(f"    Embedding batch {i // batch_size + 1}...")
    return all_embeddings


def rerank(query: str, documents: list[str], top_k: int = 10) -> list[dict]:
    """Rerank documents using Voyage rerank model."""
    client = _get_client()
    result = client.rerank(
        query=query,
        documents=documents,
        model=settings.voyage_rerank_model,
        top_k=top_k,
    )
    return [{"index": r.index, "relevance_score": r.relevance_score} for r in result.results]
