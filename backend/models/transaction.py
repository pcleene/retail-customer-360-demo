"""Transaction Pydantic models — line items, discounts, payment, loyalty."""

from pydantic import BaseModel, Field


class TransactionItem(BaseModel):
    product_id: str
    name: str = ""
    category: str
    subcategory: str
    brand: str = ""
    quantity: int
    unit_price: float
    discount_per_unit: float = 0.0
    line_total: float
    promo_id: str | None = None
    loyalty_points_earned: int = 0


class TransactionDiscount(BaseModel):
    type: str = ""
    amount_myr: float = 0.0
    code: str = ""
    description: str = ""


class TransactionPayment(BaseModel):
    method: str = ""
    card_last4: str | None = None
    RetailGroup_card_used: bool = False
    installment_months: int | None = None
    auth_code: str = ""


class TransactionLoyalty(BaseModel):
    points_earned: int = 0
    points_redeemed: int = 0
    tier_at_purchase: str = ""
    member_id: str = ""
    bonus_multiplier: float = 1.0


class Transaction(BaseModel):
    transaction_id: str
    customer_id: str
    store_id: str
    date: str
    channel: str = "in_store"
    items: list[TransactionItem] = Field(default_factory=list)
    subtotal_myr: float = 0.0
    discounts: list[TransactionDiscount] = Field(default_factory=list)
    total_discount_myr: float = 0.0
    total_myr: float
    payment: TransactionPayment = Field(default_factory=TransactionPayment)
    loyalty: TransactionLoyalty = Field(default_factory=TransactionLoyalty)
    entity: str = "RetailGroup Co"
    campaign_attribution: str | None = None
    is_returned: bool = False
