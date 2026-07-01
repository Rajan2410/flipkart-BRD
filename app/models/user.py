from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import UserRole

# Central Admin maps Hub Pickers to one or more physical warehouses.
picker_warehouse = Table(
    "picker_warehouse",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("warehouse_id", ForeignKey("warehouses.id", ondelete="CASCADE"), primary_key=True),
)


class Warehouse(Base):
    __tablename__ = "warehouses"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)  # e.g. WH01
    name: Mapped[str] = mapped_column(String(128))

    pickers: Mapped[list["User"]] = relationship(
        secondary=picker_warehouse, back_populates="warehouses"
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # The warehouse a picker has "entered" for the current working session.
    active_warehouse_id: Mapped[int | None] = mapped_column(
        ForeignKey("warehouses.id"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    warehouses: Mapped[list[Warehouse]] = relationship(
        secondary=picker_warehouse, back_populates="pickers"
    )
