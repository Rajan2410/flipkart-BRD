from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.database import get_db
from app.models.order import Order
from app.schemas.order import IngestResult, OrderOut
from app.services.ingestion import ingest_orders

router = APIRouter(prefix="/orders", tags=["orders"], dependencies=[Depends(require_admin)])


@router.post("/ingest", response_model=IngestResult)
async def ingest(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    try:
        return ingest_orders(db, file.filename or "upload.csv", content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[OrderOut])
def list_orders(
    warehouse_id: int | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(Order)
    if warehouse_id is not None:
        q = q.filter(Order.warehouse_id == warehouse_id)
    if status is not None:
        q = q.filter(Order.status == status)
    return q.order_by(Order.created_at.desc()).all()


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: str, db: Session = Depends(get_db)):
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order
