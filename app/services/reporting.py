"""Dispatch report generation.

Line-level fulfillment performance with a dynamically computed rate:
    Fulfillment_Rate = (Quantity_Picked / Quantity_Ordered) * 100

Filterable by date (order creation date), warehouse, and picker.
"""

import io
from datetime import date

import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.order import Order, OrderLine
from app.models.user import Warehouse

REPORT_COLUMNS = [
    "Order_ID", "Picker_ID", "Warehouse_ID", "Item_SKU", "Item_Name",
    "Quantity_Ordered", "Quantity_Picked", "Fulfillment_Rate",
]


def build_report_df(
    db: Session,
    *,
    report_date: date | None = None,
    warehouse_id: int | None = None,
    picker_id: int | None = None,
) -> pd.DataFrame:
    q = (
        db.query(OrderLine, Order, Warehouse.code)
        .join(Order, OrderLine.order_pk == Order.id)
        .join(Warehouse, Order.warehouse_id == Warehouse.id)
    )
    if report_date is not None:
        q = q.filter(func.date(Order.created_at) == report_date.isoformat())
    if warehouse_id is not None:
        q = q.filter(Order.warehouse_id == warehouse_id)
    if picker_id is not None:
        q = q.filter(Order.claimed_by == picker_id)

    rows = []
    for line, order, wh_code in q.all():
        rate = round((line.quantity_picked / line.quantity_ordered) * 100, 2) if line.quantity_ordered else 0.0
        rows.append({
            "Order_ID": order.order_id,
            "Picker_ID": order.claimed_by,
            "Warehouse_ID": wh_code,
            "Item_SKU": line.item_sku,
            "Item_Name": line.item_name,
            "Quantity_Ordered": line.quantity_ordered,
            "Quantity_Picked": line.quantity_picked,
            "Fulfillment_Rate": rate,
        })

    return pd.DataFrame(rows, columns=REPORT_COLUMNS)


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def to_excel_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Dispatch")
    return buf.getvalue()
