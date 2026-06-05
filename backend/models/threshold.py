"""Threshold rule documents for stream processing and agent routing."""

from pydantic import BaseModel, Field


class ThresholdCriterion(BaseModel):
    field: str = ""
    operator: str = ""
    value: float | str | list = 0
    window: str | None = None


class ActionTemplate(BaseModel):
    action_type: str = ""
    target_campaign_id: str | None = None
    notification_channel: str | None = None
    notes: str = ""


class Threshold(BaseModel):
    threshold_id: str
    signal_type: str
    name: str = ""
    description: str = ""
    severity: str = "medium"
    criteria: list[ThresholdCriterion] = Field(default_factory=list)
    target_segments: list[str] = Field(default_factory=list)
    target_tiers: list[str] = Field(default_factory=list)
    target_entities: list[str] = Field(default_factory=list)
    action_template: ActionTemplate = Field(default_factory=ActionTemplate)
    auto_process: bool = True
    cooldown_hours: int = 24
    priority: str = "medium"
    active: bool = True
    created_at: str = ""
    updated_at: str = ""
    metrics: dict = Field(default_factory=dict)
