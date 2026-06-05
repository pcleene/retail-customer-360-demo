"""Customer 360 Pydantic models — expanded for full demo narratives."""

from pydantic import BaseModel, Field


# --- Sub-models: Unified Profile ---

class ChannelOptIn(BaseModel):
    channel: str
    opted_in: bool = True
    opted_in_date: str = ""


class GeoJSONPoint(BaseModel):
    type: str = "Point"
    coordinates: list[float] = Field(default_factory=list)  # [lng, lat]


class Address(BaseModel):
    street: str = ""
    city: str = ""
    state: str = ""
    postcode: str = ""
    location: GeoJSONPoint | None = None


class CommunicationPreferences(BaseModel):
    preferred_language: str = "en"  # en, ms, zh, ta
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "08:00"
    preferred_contact_time: str = "evening"  # morning, afternoon, evening
    do_not_disturb: bool = False


class ContactInfo(BaseModel):
    email: str = ""
    phone: str = ""
    channel_opt_ins: list[ChannelOptIn] = Field(default_factory=list)
    channel_opt_outs: list[str] = Field(default_factory=list)
    communication_preferences: CommunicationPreferences = Field(
        default_factory=CommunicationPreferences
    )


class UnifiedProfile(BaseModel):
    name: str = ""
    ethnicity: str = ""
    ic_number: str = ""
    date_of_birth: str = ""
    gender: str = ""
    contact: ContactInfo = ContactInfo()
    address: Address = Address()


# --- Sub-models: Entity Profiles ---

class PreferredStore(BaseModel):
    store_id: str = ""
    visit_count: int = 0
    avg_basket_at_store_myr: float = 0.0
    last_visit: str = ""


class PointsExpiry(BaseModel):
    amount: int = 0
    expiry_date: str = ""


class RetailGroupCoProfile(BaseModel):
    member_since: str = ""
    points_balance: int = 0
    points_expiring_soon: PointsExpiry = Field(default_factory=PointsExpiry)
    preferred_stores: list[PreferredStore] = Field(default_factory=list)
    top_categories: list[str] = Field(default_factory=list)
    avg_basket_myr: float = 0.0
    visit_frequency_monthly: float = 0.0
    lifetime_visits: int = 0
    last_purchase_date: str = ""


class CreditProduct(BaseModel):
    product_code: str = ""
    product_type: str = ""  # e.g. "personal_loan", "credit_card", "auto_finance"
    product_name: str = ""
    issued_date: str = ""
    outstanding_myr: float = 0.0
    limit_myr: float = 0.0
    utilization_pct: float = 0.0
    monthly_payment_myr: float = 0.0
    interest_rate_pct: float = 0.0
    tenure_months: int | None = None
    status: str = "active"


class RetailGroupCreditProfile(BaseModel):
    member_since: str = ""
    products: list[CreditProduct] = Field(default_factory=list)
    payment_history_score: float = 0.0  # 0-1, higher = better
    total_credit_limit_myr: float = 0.0
    total_outstanding_myr: float = 0.0


class RetailGroupBankProfile(BaseModel):
    member_since: str = ""
    account_type: str = ""  # savings, current
    balance_myr: float = 0.0
    has_debit_card: bool = False
    digital_engagement_score: float = 0.0  # 0-1


class EntityProfiles(BaseModel):
    RetailGroup_co: RetailGroupCoProfile | None = None
    RetailGroup_credit: RetailGroupCreditProfile | None = None
    RetailGroup_bank: RetailGroupBankProfile | None = None


# --- Sub-models: Cross-Entity Metrics ---

class TrendPoint(BaseModel):
    month: str = ""  # "2025-01"
    value: float = 0.0


class CrossEntityMetrics(BaseModel):
    total_ltv: float = 0.0
    cross_sell_score: float = 0.0
    churn_risk: float = 0.0
    ltv_trend: list[TrendPoint] = Field(default_factory=list)
    monthly_spend_trend: list[TrendPoint] = Field(default_factory=list)


# --- Sub-models: Interaction History ---

class SupportInteraction(BaseModel):
    ticket_id: str = ""
    date: str = ""
    channel: str = ""
    agent_id: str = ""
    category: str = ""
    subcategory: str = ""
    sentiment: str = ""  # positive, neutral, negative
    resolution: str = ""
    resolution_time_minutes: int = 0
    notes: str = ""


class MarketingInteraction(BaseModel):
    campaign_id: str = ""
    content_id: str = ""
    channel: str = ""
    sent_at: str = ""
    opened_at: str | None = None
    clicked_at: str | None = None
    converted_at: str | None = None
    revenue_attributed_myr: float = 0.0


class ChannelEngagementRate(BaseModel):
    open_rate: float = 0.0
    ctr: float = 0.0
    conversion_rate: float = 0.0
    total_sent: int = 0
    last_engaged_at: str = ""


class InteractionHistory(BaseModel):
    support_interactions: list[SupportInteraction] = Field(default_factory=list)
    marketing_interactions: list[MarketingInteraction] = Field(default_factory=list)
    channel_engagement_rates: dict[str, ChannelEngagementRate] = Field(default_factory=dict)


# --- Sub-models: Brand Journey & Active Campaigns ---

class BrandJourneyMilestone(BaseModel):
    entity: str
    event: str
    date: str


class ActiveCampaign(BaseModel):
    campaign_id: str
    campaign_name: str
    enrollment_id: str = ""
    enrolled_date: str = ""
    enrolled_by: str = "agent"
    signal_id: str | None = None
    content_asset_id: str | None = None
    content_headline: str | None = None
    recommended_channel: str = ""
    reasoning: str = ""
    similar_customer_conversion_rate: float = 0.0
    expected_ltv_uplift: float = 0.0
    similar_customers_sampled: list[str] = Field(default_factory=list)
    status: str = "enrolled"  # enrolled, converted, expired, declined
    converted_at: str | None = None
    revenue_realized_myr: float = 0.0


# --- Main Customer Model ---

class Customer(BaseModel):
    customer_id: str
    unified_profile: UnifiedProfile = UnifiedProfile()
    segment: str = ""
    tier: str = ""
    entities: list[str] = Field(default_factory=list)
    entity_profiles: EntityProfiles = EntityProfiles()
    cross_entity_metrics: CrossEntityMetrics = CrossEntityMetrics()
    primary_store_id: str = ""
    join_date: str = ""
    last_visit: str = ""
    brand_journey: list[BrandJourneyMilestone] = Field(default_factory=list)
    interaction_history: InteractionHistory = InteractionHistory()
    active_campaigns: list[ActiveCampaign] = Field(default_factory=list)
    embedding: list[float] | None = None
    embedding_text: str = ""

    # Convenience accessors for backward compatibility
    @property
    def name(self) -> str:
        return self.unified_profile.name

    @property
    def state(self) -> str:
        return self.unified_profile.address.state

    @property
    def city(self) -> str:
        return self.unified_profile.address.city

    @property
    def ltv_myr(self) -> float:
        return self.cross_entity_metrics.total_ltv

    @property
    def cross_sell_score(self) -> float:
        return self.cross_entity_metrics.cross_sell_score

    @property
    def churn_risk(self) -> float:
        return self.cross_entity_metrics.churn_risk


class CustomerSummary(BaseModel):
    customer_id: str
    name: str = ""
    state: str = ""
    segment: str = ""
    tier: str = ""
    ltv_myr: float = 0.0
    cross_sell_score: float = 0.0
    churn_risk: float = 0.0
    entities: list[str] = Field(default_factory=list)
    score: float | None = None  # rank fusion score
