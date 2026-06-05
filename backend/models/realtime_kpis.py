"""Realtime KPI model — output from ASP stream processing."""

from pydantic import BaseModel, Field


class CategoryKPI(BaseModel):
    category: str = ""
    gmv_myr: float = 0.0
    txn_count: int = 0
    avg_basket_myr: float = 0.0


class StoreKPI(BaseModel):
    store_id: str = ""
    gmv_myr: float = 0.0
    txn_count: int = 0


class RealtimeKPI(BaseModel):
    window_start: str = ""
    window_end: str = ""
    total_gmv_myr: float = 0.0
    txn_count: int = 0
    avg_basket_myr: float = 0.0
    by_category: list[CategoryKPI] = Field(default_factory=list)
    by_store: list[StoreKPI] = Field(default_factory=list)
    daily_avg_gmv_myr: float = 0.0  # historical daily average for anomaly detection
    velocity_ratio: float = 1.0  # current / daily_avg — >2.0 = anomaly
