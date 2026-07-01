"""Hub Picker workflow logic: claim, scan-to-pick, skip, complete.

Concurrency: an order is locked to a single picker via an atomic conditional
UPDATE on status (PENDING -> IN_PROGRESS). Data isolation is enforced by the
caller (routes) against the picker's active warehouse.
"""

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.enums import AuditEvent, LineStatus, OrderStatus
from app.models.order import Order, OrderLine
from app.models.user import User


def _log(db: Session, *, event: AuditEvent, user_id: int, order_id: str,
         sku: str | None = None, location: str | None = None, detail: str | None = None) -> None:
    db.add(AuditLog(event=event, user_id=user_id, order_id=order_id,
                    item_sku=sku, location=location, detail=detail))


def active_line(order: Order) -> OrderLine | None:
    """First line, in route order, that is still PENDING (not picked/skipped)."""
    for ln in sorted(order.lines, key=lambda x: x.route_seq):
        if ln.status == LineStatus.PENDING:
            return ln
    return None


def claim_order(db: Session, picker: User, order: Order) -> Order:
    if order.status != OrderStatus.PENDING:
        raise HTTPException(status_code=409, detail="Order is not available to claim")

    # Atomic lock: only succeeds if still PENDING.
    result = db.execute(
        update(Order)
        .where(Order.id == order.id, Order.status == OrderStatus.PENDING)
        .values(status=OrderStatus.IN_PROGRESS, claimed_by=picker.id)
    )
    if result.rowcount == 0:
        db.rollback()
        raise HTTPException(status_code=409, detail="Order was just claimed by another picker")

    _log(db, event=AuditEvent.CLAIM, user_id=picker.id, order_id=order.order_id)
    db.commit()
    db.refresh(order)
    return order


def scan(db: Session, picker: User, order: Order, sku: str) -> dict:
    if order.status != OrderStatus.IN_PROGRESS or order.claimed_by != picker.id:
        raise HTTPException(status_code=409, detail="Order is not claimed by you or not in progress")

    line = active_line(order)
    if line is None:
        raise HTTPException(status_code=409, detail="No active pick step; order already fulfilled")

    # Enforce location-by-location: only the current step's SKU is accepted.
    if sku != line.item_sku:
        _log(db, event=AuditEvent.INVALID_SCAN, user_id=picker.id, order_id=order.order_id,
             sku=sku, location=line.location,
             detail=f"Expected {line.item_sku} at {line.location}")
        db.commit()
        raise HTTPException(
            status_code=409,
            detail=f"Wrong item. Current step expects SKU {line.item_sku} at {line.location}",
        )

    line.quantity_picked += 1
    _log(db, event=AuditEvent.SCAN, user_id=picker.id, order_id=order.order_id,
         sku=sku, location=line.location,
         detail=f"{line.quantity_picked}/{line.quantity_ordered}")

    completed = False
    if line.quantity_picked >= line.quantity_ordered:
        line.status = LineStatus.PICKED
        if active_line(order) is None:
            order.status = OrderStatus.COMPLETED
            order.completed_at = datetime.now(timezone.utc)
            completed = True
            _log(db, event=AuditEvent.COMPLETE, user_id=picker.id, order_id=order.order_id)

    db.commit()
    db.refresh(line)
    db.refresh(order)

    nxt = active_line(order)
    return {"line": line, "order": order, "order_completed": completed,
            "next_location": nxt.location if nxt else None}


def skip(db: Session, picker: User, order: Order) -> dict:
    if order.status != OrderStatus.IN_PROGRESS or order.claimed_by != picker.id:
        raise HTTPException(status_code=409, detail="Order is not claimed by you or not in progress")

    line = active_line(order)
    if line is None:
        raise HTTPException(status_code=409, detail="No active pick step to skip")

    line.status = LineStatus.SKIPPED
    _log(db, event=AuditEvent.SKIP, user_id=picker.id, order_id=order.order_id,
         sku=line.item_sku, location=line.location,
         detail=f"Skipped at {line.quantity_picked}/{line.quantity_ordered}")

    completed = False
    if active_line(order) is None:
        order.status = OrderStatus.COMPLETED
        order.completed_at = datetime.now(timezone.utc)
        completed = True
        _log(db, event=AuditEvent.COMPLETE, user_id=picker.id, order_id=order.order_id)

    db.commit()
    db.refresh(order)
    nxt = active_line(order)
    return {"line": line, "order": order, "order_completed": completed,
            "next_location": nxt.location if nxt else None}
