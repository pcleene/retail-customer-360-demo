"""Product Pydantic models — expanded for full demo narratives."""

from pydantic import BaseModel, Field


class PriceHistoryEntry(BaseModel):
    date: str = ""
    price_myr: float = 0.0


class Price(BaseModel):
    current_myr: float = 0.0
    msrp_myr: float = 0.0
    price_history: list[PriceHistoryEntry] = Field(default_factory=list)


class StoreInventory(BaseModel):
    store_id: str = ""
    units: int = 0
    shelf_location: str = ""
    last_restock: str = ""
    safety_stock: int = 0
    days_of_supply: float = 0.0


class Inventory(BaseModel):
    total_units: int = 0
    by_store: list[StoreInventory] = Field(default_factory=list)


class VelocityByStore(BaseModel):
    store_id: str = ""
    units_per_month: float = 0.0


class FrequentlyBoughtWith(BaseModel):
    product_id: str = ""
    co_purchase_rate: float = 0.0
    lift: float = 0.0


class Performance(BaseModel):
    revenue_ytd: float = 0.0
    units_sold_ytd: int = 0
    revenue_last_quarter_myr: float = 0.0
    revenue_yoy_pct: float = 0.0
    margin_pct: float = 0.0
    return_rate_pct: float = 0.0
    frequently_bought_with: list[FrequentlyBoughtWith] = Field(default_factory=list)
    velocity_by_store: list[VelocityByStore] = Field(default_factory=list)


class Promotion(BaseModel):
    promo_id: str = ""
    name: str = ""
    discount_pct: float = 0.0
    start_date: str = ""
    end_date: str = ""
    status: str = "active"


class Promotions(BaseModel):
    active_promos: list[Promotion] = Field(default_factory=list)
    promo_history: list[Promotion] = Field(default_factory=list)


class Product(BaseModel):
    product_id: str
    name: str
    category: str
    subcategory: str
    category_hierarchy: list[str] = Field(default_factory=list)  # e.g. ["grocery", "beverages", "milk"]
    brand: str = ""
    supplier_id: str = ""
    entity: str = "RetailGroup Co"
    price: Price = Price()
    inventory: Inventory = Inventory()
    performance: Performance = Performance()
    promotions: Promotions = Promotions()
    lifecycle_stage: str = "mature"  # new, growing, mature, declining, clearance
    attributes: dict = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    embedding: list[float] | None = None
    embedding_text: str = ""
