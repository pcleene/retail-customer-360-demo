"""Build Atlas Search compound clauses from SearchFilters.

Clause types:
  - Scoring (compound.must) — boost results that match selected criteria
  - Range scoring (compound.should + near) — gradient score for numeric fields
  - Hard filters (compound.filter) — binary exclusion for range cutoffs
  - Facet hard filters (compound.filter) — sidebar facet clicks
  - Vector prefilter — MQL dict for $vectorSearch pre-filter
"""

from backend.models.search import SearchFilters


def build_scoring_clauses(filters: SearchFilters) -> list[dict]:
    """compound.must clauses for segmentation criteria — CONTRIBUTE TO SCORE."""
    clauses: list[dict] = []

    field_map = {
        "tier": filters.tiers,
        "segment": filters.segments,
        "unified_profile.address.state": filters.states,
        "entities": filters.entities,
        "unified_profile.gender": filters.genders,
        "unified_profile.ethnicity": filters.ethnicities,
    }

    for path, values in field_map.items():
        if not values:
            continue
        if len(values) == 1:
            clauses.append({"text": {"query": values[0], "path": path}})
        else:
            clauses.append({
                "compound": {
                    "should": [
                        {"text": {"query": v, "path": path}} for v in values
                    ],
                    "minimumShouldMatch": 1,
                }
            })

    return clauses


def build_range_scoring_clauses(filters: SearchFilters) -> list[dict]:
    """compound.should clauses using 'near' for numeric range — SCORE GRADIENT."""
    clauses: list[dict] = []

    if filters.ltv_min is not None or filters.ltv_max is not None:
        origin = filters.ltv_max or 100000
        clauses.append({
            "near": {"path": "cross_entity_metrics.total_ltv", "origin": origin, "pivot": 20000}
        })

    if filters.cross_sell_score_min is not None or filters.cross_sell_score_max is not None:
        clauses.append({
            "near": {"path": "cross_entity_metrics.cross_sell_score", "origin": 1.0, "pivot": 0.2}
        })

    if filters.churn_risk_min is not None or filters.churn_risk_max is not None:
        clauses.append({
            "near": {"path": "cross_entity_metrics.churn_risk", "origin": 0.0, "pivot": 0.15}
        })

    return clauses


def build_hard_filters(filters: SearchFilters) -> list[dict]:
    """compound.filter clauses for hard cutoffs on numeric ranges."""
    clauses: list[dict] = []

    range_fields = [
        ("cross_entity_metrics.total_ltv", filters.ltv_min, filters.ltv_max),
        ("cross_entity_metrics.cross_sell_score", filters.cross_sell_score_min, filters.cross_sell_score_max),
        ("cross_entity_metrics.churn_risk", filters.churn_risk_min, filters.churn_risk_max),
    ]
    for path, lo, hi in range_fields:
        if lo is not None:
            clauses.append({"range": {"path": path, "gte": lo}})
        if hi is not None:
            clauses.append({"range": {"path": path, "lte": hi}})

    return clauses


def build_facet_hard_filters(filters: SearchFilters) -> list[dict]:
    """compound.filter clauses for facet sidebar clicks (hard exclusion)."""
    clauses: list[dict] = []

    field_map = {
        "segment": filters.facet_segments,
        "tier": filters.facet_tiers,
        "unified_profile.address.state": filters.facet_states,
        "entities": filters.facet_entities,
        "unified_profile.gender": filters.facet_genders,
        "unified_profile.ethnicity": filters.facet_ethnicities,
    }

    for path, values in field_map.items():
        if not values:
            continue
        if len(values) == 1:
            clauses.append({"equals": {"path": path, "value": values[0]}})
        else:
            clauses.append({
                "compound": {
                    "should": [
                        {"equals": {"path": path, "value": v}} for v in values
                    ],
                    "minimumShouldMatch": 1,
                }
            })

    return clauses


def build_compound_query(
    base_operator: dict,
    scoring_clauses: list[dict],
    range_scoring: list[dict],
    hard_filters: list[dict],
) -> dict:
    """Assemble the full compound query from all clause types."""
    must = [base_operator] + scoring_clauses

    compound: dict = {"must": must}
    if range_scoring:
        compound["should"] = range_scoring
    if hard_filters:
        compound["filter"] = hard_filters

    return {"compound": compound}


def build_vector_prefilter(filters: SearchFilters) -> dict:
    """MQL filter dict for $vectorSearch pre-filter.

    Merges scoring criteria + facet hard filters using nested schema paths.
    """
    vf: dict = {}

    field_map = {
        "segment": (filters.segments, filters.facet_segments),
        "tier": (filters.tiers, filters.facet_tiers),
        "unified_profile.address.state": (filters.states, filters.facet_states),
        "entities": (filters.entities, filters.facet_entities),
        "unified_profile.gender": (filters.genders, filters.facet_genders),
        "unified_profile.ethnicity": (filters.ethnicities, filters.facet_ethnicities),
    }
    for path, (scoring_vals, facet_vals) in field_map.items():
        values = facet_vals if facet_vals else scoring_vals
        if not values:
            continue
        vf[path] = values[0] if len(values) == 1 else {"$in": values}

    return vf
