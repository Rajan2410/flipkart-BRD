from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import AuditEvent


class AuditLog(Base):
    """Immutable transaction history: every scan, skip, or completion."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
    event: Mapped[AuditEvent] = mapped_column(Enum(AuditEvent))

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    order_id: Mapped[str] = mapped_column(String(64), index=True)
    item_sku: Mapped[str | None] = mapped_column(String(64), nullable=True)
    location: Mapped[str | None] = mapped_column(String(128), nullable=True)
    detail: Mapped[str | None] = mapped_column(String(255), nullable=True)
