from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import LineStatus, OrderStatus


# --- Master location ---
class MasterLocationCreate(BaseModel):
    warehouse_id: int
    item_sku: str = Field(..., max_length=64)
    item_name: str = Field(..., max_length=255)
    location: str = Field(..., max_length=128)


class MasterLocationOut(MasterLocationCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


# --- Orders ---
class OrderLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    item_sku: str
    item_name: str
    location: str | None
    quantity_ordered: int
    quantity_picked: int
    route_seq: int
    status: LineStatus


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    order_id: str
    customer_id: str
    warehouse_id: int
    status: OrderStatus
    claimed_by: int | None
    created_at: datetime
    completed_at: datetime | None
    lines: list[OrderLineOut] = []


class IngestResult(BaseModel):
    orders_created: int
    lines_created: int
    lines_unmapped: int
    warnings: list[str] = []


# --- Picking ---
class ScanRequest(BaseModel):
    item_sku: str = Field(..., max_length=64)


class ScanResult(BaseModel):
    accepted: bool
    message: str
    line: OrderLineOut | None = None
    next_location: str | None = None
    order_completed: bool = False
