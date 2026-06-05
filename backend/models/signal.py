"""Cross-sell signal / alert document models."""

from pydantic import BaseModel, Field


class SignalEvent(BaseModel):
    """An individual event that contributed to the signal."""

    event_type: str = ""
    event_id: str = ""
    timestamp: str = ""
    summary: str = ""
    payload: dict = Field(default_factory=dict)


class RuleSnapshot(BaseModel):
    """Frozen copy of the threshold rule that fired."""

    threshold_id: str = ""
    signal_type: str = ""
    threshold_value: float = 0.0
    operator: str = "gte"
    window: str = ""
    description: str = ""


class SignalContext(BaseModel):
    """Customer state at signal time — frozen snapshot for reasoning."""

    customer_id: str = ""
    tier: str = ""
    segment: str = ""
    entities: list[str] = Field(default_factory=list)
    total_ltv: float = 0.0
    cross_sell_score: float = 0.0
    churn_risk: float = 0.0
    primary_store_id: str = ""


class CrossSellSignal(BaseModel):
    signal_id: str
    customer_id: str
    signal_type: str
    severity: str = "medium"
    score: float = 0.0
    title: str = ""
    description: str = ""
    events: list[SignalEvent] = Field(default_factory=list)
    rule_snapshot: RuleSnapshot = Field(default_factory=RuleSnapshot)
    context: SignalContext = Field(default_factory=SignalContext)
    suggested_actions: list[str] = Field(default_factory=list)
    source: str = "stream_processor"
    window_start: str | None = None
    window_end: str | None = None
    processed: bool = False
    processed_at: str | None = None
    processed_by: str | None = None
    enrollment_id: str | None = None
    result: dict | None = None
    created_at: str = ""
