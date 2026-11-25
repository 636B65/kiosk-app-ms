from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_ORDER_QUANTITY = 1000
MAX_ORDER_ITEMS = 50
MAX_NOTES_LENGTH = 500


class OrderItemIn(BaseModel):
    product_id: int
    quantity: int = 1

    @field_validator("quantity")
    @classmethod
    def _validate_quantity(cls, v: int) -> int:
        if v < 1:
            raise ValueError("quantity must be at least 1")
        if v > MAX_ORDER_QUANTITY:
            raise ValueError(f"quantity must not exceed {MAX_ORDER_QUANTITY}")
        return v


class OrderCreate(BaseModel):
    customer_username: str
    items: List[OrderItemIn]
    notes: str = ""
    customer_pin: Optional[str] = Field(default=None, max_length=16)

    @field_validator("items")
    @classmethod
    def _validate_items(cls, v: List[OrderItemIn]) -> List[OrderItemIn]:
        if not v:
            raise ValueError("order must contain at least one item")
        if len(v) > MAX_ORDER_ITEMS:
            raise ValueError(f"order must contain at most {MAX_ORDER_ITEMS} items")
        return v

    @field_validator("notes")
    @classmethod
    def _validate_notes(cls, v: str) -> str:
        if len(v) > MAX_NOTES_LENGTH:
            raise ValueError(f"notes must not exceed {MAX_NOTES_LENGTH} characters")
        return v


class OrderItemOut(BaseModel):
    id: int
    product_id: Optional[int] = None
    product_name: str
    quantity: int
    unit_price: float

    model_config = ConfigDict(from_attributes=True)


class OrderItemInternalOut(OrderItemOut):
    unit_cost: Optional[float] = None


class OrderOut(BaseModel):
    id: int
    status: str
    subtotal: float
    total: float
    notes: str
    customer_username: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    due_date: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class OrderDetailOut(OrderOut):
    items: List[OrderItemOut] = []


class OrderExportOut(OrderOut):
    customer_id: Optional[int] = None
    items: List[OrderItemInternalOut] = []


class MonthAgg(BaseModel):
    month: str
    orders: int = 0
    spent: float = 0.0


class WeekdayAgg(BaseModel):
    day: str
    orders: int = 0
    spent: float = 0.0


class CustomerStats(BaseModel):
    orders: int = 0
    paid_orders: int = 0
    pending_orders: int = 0
    cancelled_orders: int = 0
    total_spent: float = 0.0
    total_paid: float = 0.0
    balance: float = 0.0
    avg_order: float = 0.0
    items_bought: int = 0
    first_order_at: Optional[datetime] = None
    last_order_at: Optional[datetime] = None
    last_paid_at: Optional[datetime] = None
    last_paid_amount: float = 0.0
    top_item: Optional[str] = None
    top_item_qty: int = 0
    avg_orders_per_month: float = 0.0
    busiest_day: Optional[str] = None
    orders_per_month: List[MonthAgg] = []
    orders_by_weekday: List[WeekdayAgg] = []
    next_due_date: Optional[datetime] = None


class FavoriteOut(BaseModel):
    product_id: int
    name: str
    quantity: int


class CustomerHistoryOut(BaseModel):
    balance: float = 0.0
    total_paid: float = 0.0
    orders: List[OrderDetailOut] = []
    stats: CustomerStats
    favorites: List[FavoriteOut] = []


class CustomerSummary(BaseModel):
    balance: float = 0.0
    total_paid: float = 0.0
    order_count: int = 0
    stats: CustomerStats


class CustomersStatsOut(BaseModel):
    next_due_date: Optional[datetime] = None
    customers: dict[str, CustomerSummary] = {}


MAX_MONEY_AMOUNT = 10_000_000


class SettleIn(BaseModel):
    actor: str = Field(max_length=200)
    action: str = Field(max_length=200)
    # What the customer paid on top of the debt; booked in the same transaction.
    customer_id: Optional[int] = None
    extra_amount: float = Field(default=0.0, ge=0, le=MAX_MONEY_AMOUNT)
    extra_note: str = Field(default="", max_length=200)


class ExtraPaymentCreate(BaseModel):
    """Internal: the customer service books an extra payment without settling."""

    actor: str = Field(max_length=200)
    customer_id: Optional[int] = None
    amount: float = Field(gt=0, le=MAX_MONEY_AMOUNT)
    note: str = Field(default="", max_length=200)


class PurchaseIn(BaseModel):
    amount: float = Field(gt=0, le=MAX_MONEY_AMOUNT)
    # Any past date: a batch bought earlier can be entered afterwards. Default today (UTC).
    purchased_on: Optional[date] = None
    supplier: str = Field(default="", max_length=100)
    note: str = Field(default="", max_length=200)


class PurchaseUpdate(BaseModel):
    amount: Optional[float] = Field(default=None, gt=0, le=MAX_MONEY_AMOUNT)
    purchased_on: Optional[date] = None
    supplier: Optional[str] = Field(default=None, max_length=100)
    note: Optional[str] = Field(default=None, max_length=200)


class PurchaseOut(BaseModel):
    id: int
    purchased_on: date
    amount: float
    supplier: str = ""
    note: str = ""
    created_by: str = ""
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ExtraPaymentOut(BaseModel):
    id: int
    username: str
    amount: float
    note: str = ""
    created_by: str = ""
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
