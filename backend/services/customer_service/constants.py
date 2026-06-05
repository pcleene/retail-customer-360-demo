"""Shared constants for customer search — index names, paths, projections, facets."""

SEARCH_INDEX = "customers_search"
VECTOR_INDEX = "customers_vector"

TEXT_PATHS = [
    "unified_profile.name",
    "unified_profile.address.city",
    "unified_profile.address.state",
    "unified_profile.ethnicity",
    "tier",
    "segment",
    "entities",
    "embedding_text",
    "entity_profiles.RetailGroup_co.top_categories",
    "entity_profiles.RetailGroup_credit.products.product_name",
]

RESULT_PROJECTION = {
    "_id": 0,
    "customer_id": 1,
    "unified_profile.name": 1,
    "unified_profile.address.city": 1,
    "unified_profile.address.state": 1,
    "unified_profile.ethnicity": 1,
    "unified_profile.gender": 1,
    "segment": 1,
    "tier": 1,
    "entities": 1,
    "cross_entity_metrics.total_ltv": 1,
    "cross_entity_metrics.cross_sell_score": 1,
    "cross_entity_metrics.churn_risk": 1,
    "primary_store_id": 1,
    "join_date": 1,
    "last_visit": 1,
}

FACET_DEFINITIONS = {
    "segmentFacet": {"type": "string", "path": "segment"},
    "tierFacet": {"type": "string", "path": "tier"},
    "stateFacet": {"type": "string", "path": "unified_profile.address.state", "numBuckets": 16},
    "entityFacet": {"type": "string", "path": "entities"},
    "genderFacet": {"type": "string", "path": "unified_profile.gender"},
    "ethnicityFacet": {"type": "string", "path": "unified_profile.ethnicity"},
}

FACET_KEY_MAP = {
    "segmentFacet": "segments",
    "tierFacet": "tiers",
    "stateFacet": "states",
    "entityFacet": "entities",
    "genderFacet": "genders",
    "ethnicityFacet": "ethnicities",
}
