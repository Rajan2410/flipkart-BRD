from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import require_picker
from app.core.database import get_db
from app.models.enums import OrderStatus
from app.models.order import Order
from app.models.user import User
from app.schemas.order import OrderOut, ScanRequest, ScanResult
from app.schemas.user import EnterWarehouseRequest, UserOut
from app.services import picking

router = APIRouter(prefix="/picking", tags=["picking"])


def _load_order_in_scope(db: Session, picker: User, order_id: str) -> Order:
    """Fetch an order and enforce warehouse data-isolation for the picker."""
    if picker.active_warehouse_id is None:
        raise HTTPException(status_code=409, detail="Enter a warehouse first")
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.warehouse_id != picker.active_warehouse_id:
        # Do not leak existence of out-of-scope orders.
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.post("/enter-warehouse", response_model=UserOut)
def enter_warehouse(
    payload: EnterWarehouseRequest,
    picker: User = Depends(require_picker),
    db: Session = Depends(get_db),
):
    allowed = {w.id for w in picker.warehouses}
    if payload.warehouse_id not in allowed:
        raise HTTPException(status_code=403, detail="You are not mapped to this warehouse")
    picker.active_warehouse_id = payload.warehouse_id
    db.commit()
    db.refresh(picker)
    return picker


@router.get("/queue", response_model=list[OrderOut])
def pick_queue(picker: User = Depends(require_picker), db: Session = Depends(get_db)):
    if picker.active_warehouse_id is None:
        raise HTTPException(status_code=409, detail="Enter a warehouse first")
    return (
        db.query(Order)
        .filter(
            Order.warehouse_id == picker.active_warehouse_id,
            Order.status == OrderStatus.PENDING,
        )
        .order_by(Order.created_at)
        .all()
    )


@router.get("/my-orders", response_model=list[OrderOut])
def my_orders(picker: User = Depends(require_picker), db: Session = Depends(get_db)):
    return (
        db.query(Order)
        .filter(Order.claimed_by == picker.id, Order.status == OrderStatus.IN_PROGRESS)
        .all()
    )


@router.get("/orders/{order_id}", response_model=OrderOut)
def view_order(order_id: str, picker: User = Depends(require_picker), db: Session = Depends(get_db)):
    return _load_order_in_scope(db, picker, order_id)


@router.post("/orders/{order_id}/claim", response_model=OrderOut)
def claim(order_id: str, picker: User = Depends(require_picker), db: Session = Depends(get_db)):
    order = _load_order_in_scope(db, picker, order_id)
    return picking.claim_order(db, picker, order)


@router.post("/orders/{order_id}/scan", response_model=ScanResult)
def scan_item(
    order_id: str,
    payload: ScanRequest,
    picker: User = Depends(require_picker),
    db: Session = Depends(get_db),
):
    order = _load_order_in_scope(db, picker, order_id)
    r = picking.scan(db, picker, order, payload.item_sku)
    return ScanResult(
        accepted=True,
        message="Picked" if not r["order_completed"] else "Order fulfilled",
        line=r["line"],
        next_location=r["next_location"],
        order_completed=r["order_completed"],
    )


@router.post("/orders/{order_id}/skip", response_model=ScanResult)
def skip_step(order_id: str, picker: User = Depends(require_picker), db: Session = Depends(get_db)):
    order = _load_order_in_scope(db, picker, order_id)
    r = picking.skip(db, picker, order)
    return ScanResult(
        accepted=True,
        message="Step skipped" if not r["order_completed"] else "Order closed",
        line=r["line"],
        next_location=r["next_location"],
        order_completed=r["order_completed"],
    )
