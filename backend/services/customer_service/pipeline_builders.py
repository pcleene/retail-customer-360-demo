"""Build complete aggregation pipelines for Atlas Search / Vector Search / Rank Fusion."""

from .constants import SEARCH_INDEX, VECTOR_INDEX, TEXT_PATHS, RESULT_PROJECTION, FACET_DEFINITIONS
from .clause_builders import build_compound_query


def build_rankfusion_pipeline(
    query: str,
    scoring_clauses: list[dict],
    range_scoring: list[dict],
    hard_filters: list[dict],
    query_embedding: list[float],
    vector_prefilter: dict,
    limit: int,
    skip: int = 0,
) -> list[dict]:
    """$rankFusion: text + vector hybrid. Uses $skip for page 2+
    because $rankFusion doesn't support searchSequenceToken."""

    fetch_limit = skip + limit + 1

    text_operator = {"text": {"query": query, "path": TEXT_PATHS, "fuzzy": {"maxEdits": 1}}}
    text_compound = build_compound_query(text_operator, scoring_clauses, range_scoring, hard_filters)
    text_stage: dict = {"$search": {"index": SEARCH_INDEX, **text_compound}}

    vector_stage: dict = {
        "$vectorSearch": {
            "index": VECTOR_INDEX,
            "path": "embedding",
            "queryVector": query_embedding,
            "numCandidates": fetch_limit * 10,
            "limit": fetch_limit,
        }
    }
    if vector_prefilter:
        vector_stage["$vectorSearch"]["filter"] = vector_prefilter

    pipeline: list[dict] = [
        {
            "$rankFusion": {
                "input": {
                    "pipelines": {
                        "textSearch": [text_stage, {"$limit": fetch_limit}],
                        "vectorSearch": [vector_stage],
                    }
                },
                "combination": {
                    "weights": {
                        "vectorSearch": 0.7,
                        "textSearch": 0.3,
                    }
                },
            }
        },
        {"$addFields": {"rank_fusion_score": {"$meta": "score"}}},
    ]
    if skip > 0:
        pipeline.append({"$skip": skip})
    pipeline.append({"$limit": limit + 1})
    pipeline.append({"$project": {**RESULT_PROJECTION, "rank_fusion_score": 1}})
    return pipeline


def build_vector_only_pipeline(
    query_embedding: list[float],
    vector_prefilter: dict,
    limit: int,
    skip: int = 0,
) -> list[dict]:
    """$vectorSearch-only fallback. Uses $skip for page 2+."""
    fetch_limit = skip + limit + 1
    vector_stage: dict = {
        "$vectorSearch": {
            "index": VECTOR_INDEX,
            "path": "embedding",
            "queryVector": query_embedding,
            "numCandidates": fetch_limit * 10,
            "limit": fetch_limit,
        }
    }
    if vector_prefilter:
        vector_stage["$vectorSearch"]["filter"] = vector_prefilter

    pipeline: list[dict] = [
        vector_stage,
        {"$addFields": {"rank_fusion_score": {"$meta": "vectorSearchScore"}}},
    ]
    if skip > 0:
        pipeline.append({"$skip": skip})
    pipeline.append({"$limit": limit + 1})
    pipeline.append({"$project": {**RESULT_PROJECTION, "rank_fusion_score": 1}})
    return pipeline


def build_search_pipeline(
    query: str,
    scoring_clauses: list[dict],
    range_scoring: list[dict],
    hard_filters: list[dict],
    cursor: str | None,
    limit: int,
) -> list[dict]:
    """$search pipeline with searchSequenceToken pagination."""
    if query.strip():
        base_op = {"text": {"query": query, "path": TEXT_PATHS, "fuzzy": {"maxEdits": 1}}}
    else:
        base_op = {"exists": {"path": "customer_id"}}

    has_clauses = scoring_clauses or range_scoring or hard_filters

    search_cmd: dict = {"index": SEARCH_INDEX}
    if has_clauses:
        compound = build_compound_query(base_op, scoring_clauses, range_scoring, hard_filters)
        search_cmd.update(compound)
    else:
        op_key = list(base_op.keys())[0]
        search_cmd[op_key] = base_op[op_key]

    if cursor:
        search_cmd["searchAfter"] = cursor

    return [
        {"$search": search_cmd},
        {"$addFields": {
            "score": {"$meta": "searchScore"},
            "paginationToken": {"$meta": "searchSequenceToken"},
        }},
        {"$limit": limit + 1},
        {"$project": {**RESULT_PROJECTION, "score": 1, "paginationToken": 1}},
    ]


def build_facet_pipeline(
    query: str,
    scoring_clauses: list[dict],
    range_scoring: list[dict],
    hard_filters: list[dict],
) -> list[dict]:
    """$searchMeta for facet counts. O(1) via Atlas Search index."""
    if query.strip():
        base_op = {"text": {"query": query, "path": TEXT_PATHS, "fuzzy": {"maxEdits": 1}}}
    else:
        base_op = {"exists": {"path": "customer_id"}}

    has_clauses = scoring_clauses or range_scoring or hard_filters

    if has_clauses:
        operator = build_compound_query(base_op, scoring_clauses, range_scoring, hard_filters)
    else:
        operator = base_op

    return [{
        "$searchMeta": {
            "index": SEARCH_INDEX,
            "facet": {
                "operator": operator,
                "facets": FACET_DEFINITIONS,
            },
        }
    }]


def parse_facets(meta: dict) -> dict:
    """Transform $searchMeta facet output into {key: {value: count}} format."""
    from .constants import FACET_KEY_MAP

    facet_data = meta.get("facet", {})
    parsed: dict = {}
    for facet_name, response_key in FACET_KEY_MAP.items():
        buckets = facet_data.get(facet_name, {}).get("buckets", [])
        if buckets:
            parsed[response_key] = {
                b["_id"]: b["count"]
                for b in buckets
                if b.get("_id") and b.get("count", 0) > 0
            }
    return parsed
