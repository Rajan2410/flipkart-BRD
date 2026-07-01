"""Order ingestion from CSV/Excel.

Expected columns (case-insensitive):
    Order_ID, Customer_ID, Warehouse_ID, Item_SKU, Item_Name, Quantity_Ordered

Warehouse_ID in the file refers to the warehouse *code* (e.g. WH01).
Locations are resolved from MasterLocation at ingest time and lines are
pre-sequenced with the routing engine so pickers get a ready walk-path.
"""

import io

import pandas as pd
from sqlalchemy.orm import Session

from app.models.location import MasterLocation
from app.models.order import Order, OrderLine
from app.models.user import Warehouse
from app.schemas.order import IngestResult
from app.services.routing import order_lines_by_route

REQUIRED_COLUMNS = [
    "order_id",
    "customer_id",
    "warehouse_id",
    "item_sku",
    "item_name",
    "quantity_ordered",
]


def _read_dataframe(filename: str, content: bytes) -> pd.DataFrame:
    name = filename.lower()
    buf = io.BytesIO(content)
    if name.endswith(".csv"):
        df = pd.read_csv(buf)
    elif name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(buf)
    else:
        raise ValueError("Unsupported file type. Use .csv, .xlsx, or .xls")
    df.columns = [str(c).strip().lower() for c in df.columns]
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    return df


def ingest_orders(db: Session, filename: str, content: bytes) -> IngestResult:
    df = _read_dataframe(filename, content)

    warnings: list[str] = []
    orders_created = lines_created = lines_unmapped = 0

    # Cache warehouse code -> id and (wh_id, sku) -> location.
    wh_by_code = {w.code: w for w in db.query(Warehouse).all()}

    for order_id, group in df.groupby("order_id"):
        order_id = str(order_id).strip()
        first = group.iloc[0]
        wh_code = str(first["warehouse_id"]).strip()
        warehouse = wh_by_code.get(wh_code)
        if warehouse is None:
            warnings.append(f"Order {order_id}: unknown warehouse '{wh_code}' — skipped")
            continue

        if db.query(Order).filter(Order.order_id == order_id).first():
            warnings.append(f"Order {order_id}: already exists — skipped")
            continue

        order = Order(
            order_id=order_id,
            customer_id=str(first["customer_id"]).strip(),
            warehouse_id=warehouse.id,
        )

        lines: list[OrderLine] = []
        for _, row in group.iterrows():
            try:
                qty = int(row["quantity_ordered"])
            except (ValueError, TypeError):
                warnings.append(f"Order {order_id} SKU {row['item_sku']}: invalid quantity — skipped")
                continue
            if qty <= 0:
                warnings.append(f"Order {order_id} SKU {row['item_sku']}: quantity must be positive — skipped")
                continue

            sku = str(row["item_sku"]).strip()
            master = (
                db.query(MasterLocation)
                .filter(MasterLocation.warehouse_id == warehouse.id, MasterLocation.item_sku == sku)
                .first()
            )
            location = master.location if master else None
            if location is None:
                lines_unmapped += 1
                warnings.append(f"Order {order_id} SKU {sku}: no master location — will sort last")

            lines.append(
                OrderLine(
                    item_sku=sku,
                    item_name=str(row["item_name"]).strip(),
                    location=location,
                    quantity_ordered=qty,
                )
            )

        if not lines:
            warnings.append(f"Order {order_id}: no valid lines — skipped")
            continue

        # Pre-compute the optimized walk-path sequence.
        for seq, ln in enumerate(order_lines_by_route(lines)):
            ln.route_seq = seq

        order.lines = lines
        db.add(order)
        orders_created += 1
        lines_created += len(lines)

    db.commit()
    return IngestResult(
        orders_created=orders_created,
        lines_created=lines_created,
        lines_unmapped=lines_unmapped,
        warnings=warnings,
    )
