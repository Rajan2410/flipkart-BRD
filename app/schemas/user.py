from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import UserRole


class WarehouseCreate(BaseModel):
    code: str = Field(..., max_length=32)
    name: str = Field(..., max_length=128)


class WarehouseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str


class UserCreate(BaseModel):
    username: str = Field(..., max_length=64)
    password: str = Field(..., min_length=6)
    role: UserRole = UserRole.HUB_PICKER


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    role: UserRole
    is_active: bool
    active_warehouse_id: int | None = None


class PickerMappingRequest(BaseModel):
    """Assign the set of warehouses a picker is allowed to operate in."""
    warehouse_ids: list[int]


class EnterWarehouseRequest(BaseModel):
    warehouse_id: int
