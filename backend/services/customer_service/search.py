"""Unified hybrid search entry point — orchestrates all search strategies."""

import logging
import time

from backend.database import get_db
from backend.models.search import SearchFilters
from backend.query_log import log_query
from backend.services.embedding_service import embed_for_query

from .clause_builders import (
    build_scoring_clauses,
    build_range_scoring_clauses,
    build_hard_filters,
    build_facet_hard_filters,
    build_vector_prefilter,
)
from .pipeline_builders import (
    build_rankfusion_pipeline,
    build_vector_only_pipeline,
    build_search_pipeline,
    build_facet_pipeline,
    parse_facets,
)

logger = logging.getLogger(__name__)


async def search_customers_hybrid(filters: SearchFilters) -> dict:
    """Unified search entry point. ALL queries go through Atlas Search.

    Strategy:
      1. Build scoring + hard filter clauses from all params
      2. Has text query → try $rankFusion, fall back to $vectorSearch, then $search
         ($rankFusion/$vectorSearch use $skip for page 2+)
      3. Has cursor or no text → $search with searchAfter
      4. Facets via $searchMeta (first page only, separate pipeline — required
         because $searchMeta cannot be nested inside $rankFusion)
    """
    db = get_db()
    coll = db["customers"]

    has_query = bool(filters.query and filters.query.strip())
    has_cursor = bool(filters.cursor)
    limit = filters.page_size
    page = max(filters.page, 1)
    skip = (page - 1) * limit

    scoring_clauses = build_scoring_clauses(filters)
    range_scoring = build_range_scoring_clauses(filters)
    hard_filters = build_hard_filters(filters) + build_facet_hard_filters(filters)
    vector_prefilter = build_vector_prefilter(filters)

    results: list[dict] = []
    search_method = "structured"

    if has_query and not has_cursor:
        # $rankFusion / $vectorSearch path — uses $skip for page 2+
        query_embedding = None
        try:
            query_embedding = embed_for_query(filters.query)
        except Exception as e:
            logger.warning("Embedding generation failed: %s", e)

        if query_embedding:
            try:
                pipeline = build_rankfusion_pipeline(
                    filters.query, scoring_clauses, range_scoring, hard_filters,
                    query_embedding, vector_prefilter, limit, skip,
                )
                t0 = time.perf_counter()
                async for doc in await coll.aggregate(pipeline):
                    results.append(doc)
                log_query("customers", "aggregate", pipeline, (time.perf_counter() - t0) * 1000, result=results)
                search_method = "rankFusion"
            except Exception as e:
                logger.warning("$rankFusion failed (%s), trying $vectorSearch", e)

            if not results:
                try:
                    pipeline = build_vector_only_pipeline(query_embedding, vector_prefilter, limit, skip)
                    t0 = time.perf_counter()
                    async for doc in await coll.aggregate(pipeline):
                        results.append(doc)
                    log_query("customers", "aggregate", pipeline, (time.perf_counter() - t0) * 1000, result=results)
                    search_method = "vectorSearch"
                except Exception as e:
                    logger.warning("$vectorSearch failed: %s", e)

        if not results:
            try:
                pipeline = build_search_pipeline(
                    filters.query, scoring_clauses, range_scoring, hard_filters, None, limit,
                )
                t0 = time.perf_counter()
                async for doc in await coll.aggregate(pipeline):
                    results.append(doc)
                log_query("customers", "aggregate", pipeline, (time.perf_counter() - t0) * 1000, result=results)
                search_method = "textSearch"
            except Exception as e:
                logger.error("All search methods failed: %s", e)

    else:
        # $search with searchAfter cursor (structured browse or paginated text)
        try:
            pipeline = build_search_pipeline(
                filters.query, scoring_clauses, range_scoring, hard_filters, filters.cursor, limit,
            )
            t0 = time.perf_counter()
            async for doc in await coll.aggregate(pipeline):
                results.append(doc)
            log_query("customers", "aggregate", pipeline, (time.perf_counter() - t0) * 1000, result=results)
            search_method = "textSearch" if has_query else "structured"
        except Exception as e:
            logger.error("$search failed: %s", e)

    # ── Pagination: limit+1 pattern ──
    has_more = len(results) > limit
    if has_more:
        results = results[:limit]

    next_cursor = None
    if has_more and results:
        next_cursor = results[-1].get("paginationToken")

    next_page = page + 1 if has_more else None

    for r in results:
        r.pop("paginationToken", None)

    # ── Facets via separate $searchMeta pipeline (first page only) ──
    facets: dict = {}
    if not has_cursor and page <= 1:
        try:
            facet_pipeline = build_facet_pipeline(
                filters.query, scoring_clauses, range_scoring, hard_filters,
            )
            t0 = time.perf_counter()
            raw_meta: dict = {}
            async for meta in await coll.aggregate(facet_pipeline):
                raw_meta = meta
                facets = parse_facets(meta)
            log_query("customers", "aggregate", facet_pipeline, (time.perf_counter() - t0) * 1000, result=raw_meta)
        except Exception as e:
            logger.warning("$searchMeta facets failed: %s", e)

    return {
        "customers": results,
        "total": len(results),
        "facets": facets,
        "search_method": search_method,
        "pagination": {
            "hasMore": has_more,
            "nextCursor": next_cursor,
            "nextPage": next_page,
            "limit": limit,
        },
    }
