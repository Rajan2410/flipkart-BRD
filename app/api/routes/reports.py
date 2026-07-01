from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.database import get_db
from app.services import reporting

router = APIRouter(prefix="/reports", tags=["reports"], dependencies=[Depends(require_admin)])


@router.get("/dispatch")
def dispatch_report(
    format: str = Query("csv", pattern="^(csv|xlsx)$"),
    report_date: date | None = Query(None, alias="date"),
    warehouse_id: int | None = None,
    picker_id: int | None = None,
    db: Session = Depends(get_db),
):
    df = reporting.build_report_df(
        db, report_date=report_date, warehouse_id=warehouse_id, picker_id=picker_id
    )
    if format == "xlsx":
        data = reporting.to_excel_bytes(df)
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = "dispatch_report.xlsx"
    else:
        data = reporting.to_csv_bytes(df)
        media = "text/csv"
        filename = "dispatch_report.csv"
    return Response(
        content=data,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
