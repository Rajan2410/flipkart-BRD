from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MasterLocation(Base):
    """Master layout: maps an Item_SKU to a physical shelf location.

    Scoped per warehouse (the same SKU can sit at different shelves in
    different hubs), which is an intentional refinement over the BRD's
    global SKU->location assumption.
    """

    __tablename__ = "master_locations"
    __table_args__ = (UniqueConstraint("warehouse_id", "item_sku", name="uq_wh_sku"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id", ondelete="CASCADE"), index=True)
    item_sku: Mapped[str] = mapped_column(String(64), index=True)
    item_name: Mapped[str] = mapped_column(String(255))
    location: Mapped[str] = mapped_column(String(128))  # e.g. Aisle_A-Bay_04-Shelf_2
