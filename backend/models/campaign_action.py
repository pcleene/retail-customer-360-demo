"""Campaign action audit log — cross-sell agent enrollment decisions."""

from pydantic import BaseModel, Field


class AgentReasoningStep(BaseModel):
    node: str
    started_at: str = ""
    finished_at: str = ""
    summary: str = ""
    details: dict = Field(default_factory=dict)


class CampaignAction(BaseModel):
    action_id: str
    enrollment_id: str
    customer_id: str
    customer_name_snapshot: str = ""
    campaign_id: str
    campaign_name_snapshot: str = ""
    content_id: str | None = None
    recommended_channel: str = ""
    triggered_by: str = "agent"
    signal_id: str | None = None
    agent_thread_id: str = ""
    reasoning: str = ""
    reasoning_steps: list[AgentReasoningStep] = Field(default_factory=list)
    similar_customers_sampled: list[str] = Field(default_factory=list)
    similar_conversion_rate: float = 0.0
    expected_ltv_uplift: float = 0.0
    targeting_match_score: float = 0.0
    semantic_similarity: float = 0.0
    rerank_score: float = 0.0
    status: str = "enrolled"
    created_at: str = ""
    last_updated_at: str = ""
    converted_at: str | None = None
    revenue_realized_myr: float = 0.0
