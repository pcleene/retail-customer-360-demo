"""Campaign & content asset Pydantic models — expanded for full demo narratives."""

from pydantic import BaseModel, Field


# --- Sub-models: Targeting ---

class Targeting(BaseModel):
    segment_criteria: list[str] = Field(default_factory=list)
    behavior_criteria: list[str] = Field(default_factory=list)
    estimated_audience_size: int = 0
    threshold_id: str = ""


# --- Sub-models: Offer ---

class Offer(BaseModel):
    product: str = ""
    headline: str = ""
    value_proposition: str = ""
    terms: str = ""
    cta: str = ""


# --- Sub-models: Content Assets ---

class PersonalizationField(BaseModel):
    field_name: str = ""
    source: str = ""  # e.g. "customer.name", "entity_profiles.RetailGroup_co.points_balance"


class ContentAsset(BaseModel):
    content_id: str
    campaign_id: str
    campaign_name: str = ""
    channel: str = ""
    headline: str = ""
    body: str = ""
    body_template: str = ""
    image_url: str = ""
    cta_deeplink: str = ""
    target_persona: str = ""
    language: str = "en"
    tone: str = "friendly"
    cta: str = ""
    personalization_fields: list[PersonalizationField] = Field(default_factory=list)
    performance_stats: dict = Field(default_factory=dict)  # {opens, clicks, conversions}
    targeting_affinity: dict = Field(default_factory=dict)  # {segments, tiers, entities}
    best_send_time: str = "evening"
    best_send_day: str = "Friday"
    avg_engagement_window_hours: float = 0.0
    embedding: list[float] | None = None
    embedding_text: str = ""


# --- Sub-models: Performance ---

class ChannelPerformance(BaseModel):
    channel: str = ""
    sent: int = 0
    opened: int = 0
    clicked: int = 0
    converted: int = 0
    open_rate: float = 0.0
    ctr: float = 0.0
    conversion_rate: float = 0.0


class CampaignPerformance(BaseModel):
    enrollment_count: int = 0
    conversion_rate: float = 0.0
    total_revenue_myr: float = 0.0
    avg_ltv_uplift: float = 0.0
    by_channel: list[ChannelPerformance] = Field(default_factory=list)


# --- Main Campaign Model ---

class Campaign(BaseModel):
    campaign_id: str
    name: str
    type: str  # cross_sell, upsell, retention, reactivation, loyalty_upgrade
    entity: str
    description: str = ""
    targeting: Targeting = Targeting()
    offer: Offer = Offer()
    content_assets: list[str] = Field(default_factory=list)  # content_id refs
    target_segments: list[str] = Field(default_factory=list)
    target_tiers: list[str] = Field(default_factory=list)
    start_date: str = ""
    end_date: str = ""
    status: str = "active"
    budget_myr: float = 0.0
    performance: CampaignPerformance = CampaignPerformance()
    embedding: list[float] | None = None
    embedding_text: str = ""


# --- Campaign Enrollment ---

class CampaignEnrollment(BaseModel):
    customer_id: str
    customer_name: str = ""
    campaign_id: str
    campaign_name: str = ""
    enrolled_date: str = ""
    content_id: str | None = None
    content_headline: str | None = None
    recommended_channel: str = ""
    reason: str = ""
    content_reason: str = ""
    expected_ltv_uplift: float = 0.0
    targeting_match: float = 0.0
    semantic_similarity: float = 0.0
    similar_customer_conversion_rate: float = 0.0
    status: str = "enrolled"
