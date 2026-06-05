from pydantic import BaseModel


class SearchFilters(BaseModel):
    query: str = ""

    # Scoring criteria (from criteria drawer → compound.must)
    segments: list[str] = []
    tiers: list[str] = []
    states: list[str] = []
    entities: list[str] = []
    genders: list[str] = []
    ethnicities: list[str] = []

    # Range scoring + hard cutoffs (drawer → compound.should near + compound.filter range)
    churn_risk_min: float | None = None
    churn_risk_max: float | None = None
    cross_sell_score_min: float | None = None
    cross_sell_score_max: float | None = None
    ltv_min: float | None = None
    ltv_max: float | None = None

    # Facet hard filters (from facet sidebar clicks → compound.filter equals)
    facet_segments: list[str] = []
    facet_tiers: list[str] = []
    facet_states: list[str] = []
    facet_entities: list[str] = []
    facet_genders: list[str] = []
    facet_ethnicities: list[str] = []

    page_size: int = 20
    page: int = 1  # 1-indexed page number (used for $rankFusion/$vectorSearch skip-based pagination)
    cursor: str | None = None  # searchSequenceToken (used for $search pagination)


class Pagination(BaseModel):
    hasMore: bool = False
    nextCursor: str | None = None
    limit: int = 20


class SearchResult(BaseModel):
    customers: list[dict] = []
    total: int = 0
    facets: dict = {}
    search_method: str = ""
    pagination: Pagination = Pagination()


class DashboardKPIs(BaseModel):
    total_customers: int = 0
    total_opportunities: int = 0
    active_campaigns: int = 0
    avg_conversion_rate: float = 0.0
    customers_by_segment: dict = {}
    customers_by_tier: dict = {}
    avg_cross_sell_by_tier: dict = {}
    avg_churn_by_tier: dict = {}
    avg_ltv_by_segment: dict = {}
    recent_signals: list[dict] = []
