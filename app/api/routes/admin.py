from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.database import get_db
from app.core.security import hash_password
from app.models.enums import UserRole
from app.models.location import MasterLocation
from app.models.user import User, Warehouse
from app.schemas.order import MasterLocationCreate, MasterLocationOut
from app.schemas.user import (
    PickerMappingRequest,
    UserCreate,
    UserOut,
    WarehouseCreate,
    WarehouseOut,
)

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


# --- Warehouses ---
@router.post("/warehouses", response_model=WarehouseOut, status_code=201)
def create_warehouse(payload: WarehouseCreate, db: Session = Depends(get_db)):
    if db.query(Warehouse).filter(Warehouse.code == payload.code).first():
        raise HTTPException(status_code=409, detail="Warehouse code already exists")
    wh = Warehouse(code=payload.code, name=payload.name)
    db.add(wh)
    db.commit()
    db.refresh(wh)
    return wh


@router.get("/warehouses", response_model=list[WarehouseOut])
def list_warehouses(db: Session = Depends(get_db)):
    return db.query(Warehouse).order_by(Warehouse.code).all()


# --- Pickers / users ---
@router.post("/users", response_model=UserOut, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=409, detail="Username already exists")
    user = User(
        username=payload.username,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)):
    return db.query(User).order_by(User.username).all()


@router.put("/users/{user_id}/warehouses", response_model=UserOut)
def map_picker_warehouses(user_id: int, payload: PickerMappingRequest, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None or user.role != UserRole.HUB_PICKER:
        raise HTTPException(status_code=404, detail="Hub Picker not found")
    warehouses = db.query(Warehouse).filter(Warehouse.id.in_(payload.warehouse_ids)).all()
    if len(warehouses) != len(set(payload.warehouse_ids)):
        raise HTTPException(status_code=400, detail="One or more warehouse_ids are invalid")
    user.warehouses = warehouses
    db.commit()
    db.refresh(user)
    return user


# --- Master location mapping (SKU -> shelf) ---
@router.post("/locations", response_model=MasterLocationOut, status_code=201)
def create_location(payload: MasterLocationCreate, db: Session = Depends(get_db)):
    if db.get(Warehouse, payload.warehouse_id) is None:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    existing = (
        db.query(MasterLocation)
        .filter(
            MasterLocation.warehouse_id == payload.warehouse_id,
            MasterLocation.item_sku == payload.item_sku,
        )
        .first()
    )
    if existing:
        existing.location = payload.location
        existing.item_name = payload.item_name
        db.commit()
        db.refresh(existing)
        return existing
    loc = MasterLocation(**payload.model_dump())
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc


@router.post("/locations/upload")
async def upload_locations(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Bulk master-layout upload. Columns: Warehouse_ID(code), Item_SKU, Item_Name, Location."""
    import pandas as pd
    import io

    content = await file.read()
    name = (file.filename or "").lower()
    buf = io.BytesIO(content)
    df = pd.read_csv(buf) if name.endswith(".csv") else pd.read_excel(buf)
    df.columns = [str(c).strip().lower() for c in df.columns]

    wh_by_code = {w.code: w.id for w in db.query(Warehouse).all()}
    created = updated = skipped = 0
    for _, row in df.iterrows():
        wh_id = wh_by_code.get(str(row.get("warehouse_id")).strip())
        if wh_id is None:
            skipped += 1
            continue
        sku = str(row["item_sku"]).strip()
        loc = (
            db.query(MasterLocation)
            .filter(MasterLocation.warehouse_id == wh_id, MasterLocation.item_sku == sku)
            .first()
        )
        if loc:
            loc.location = str(row["location"]).strip()
            loc.item_name = str(row["item_name"]).strip()
            updated += 1
        else:
            db.add(MasterLocation(
                warehouse_id=wh_id, item_sku=sku,
                item_name=str(row["item_name"]).strip(),
                location=str(row["location"]).strip(),
            ))
            created += 1
    db.commit()
    return {"created": created, "updated": updated, "skipped": skipped}
