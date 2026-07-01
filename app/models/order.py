from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import LineStatus, OrderStatus


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # business id
    customer_id: Mapped[str] = mapped_column(String(64))
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), index=True)

    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.PENDING, index=True)
    claimed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    lines: Mapped[list["OrderLine"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="OrderLine.route_seq"
    )


class OrderLine(Base):
    __tablename__ = "order_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_pk: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)

    item_sku: Mapped[str] = mapped_column(String(64), index=True)
    item_name: Mapped[str] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(128), nullable=True)  # resolved from master

    quantity_ordered: Mapped[int] = mapped_column(Integer)
    quantity_picked: Mapped[int] = mapped_column(Integer, default=0)

    route_seq: Mapped[int] = mapped_column(Integer, default=0)  # position in optimized walk-path
    status: Mapped[LineStatus] = mapped_column(Enum(LineStatus), default=LineStatus.PENDING)

    order: Mapped[Order] = relationship(back_populates="lines")
