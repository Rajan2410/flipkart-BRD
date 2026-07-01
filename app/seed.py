"""Seed the database with a bootstrap admin and demo data.

Run:  python -m app.seed
Idempotent: safe to run multiple times.
"""

from app.core.config import settings
from app.core.database import SessionLocal, init_db
from app.core.security import hash_password
from app.models.enums import UserRole
from app.models.location import MasterLocation
from app.models.user import User, Warehouse


def seed() -> None:
    init_db()
    db = SessionLocal()
    try:
        # Bootstrap admin
        admin = db.query(User).filter(User.username == settings.FIRST_ADMIN_USERNAME).first()
        if admin is None:
            admin = User(
                username=settings.FIRST_ADMIN_USERNAME,
                hashed_password=hash_password(settings.FIRST_ADMIN_PASSWORD),
                role=UserRole.CENTRAL_ADMIN,
            )
            db.add(admin)
            print(f"Created admin '{settings.FIRST_ADMIN_USERNAME}'")

        # Demo warehouses
        for code, name in [("WH01", "Chennai Hub"), ("WH02", "Bengaluru Hub")]:
            if not db.query(Warehouse).filter(Warehouse.code == code).first():
                db.add(Warehouse(code=code, name=name))
        db.commit()

        wh01 = db.query(Warehouse).filter(Warehouse.code == "WH01").first()
        wh02 = db.query(Warehouse).filter(Warehouse.code == "WH02").first()

        # Demo picker mapped to WH01
        picker = db.query(User).filter(User.username == "picker1").first()
        if picker is None:
            picker = User(
                username="picker1",
                hashed_password=hash_password("picker123"),
                role=UserRole.HUB_PICKER,
            )
            picker.warehouses = [wh01]
            db.add(picker)
            print("Created picker 'picker1' mapped to WH01")

        # Demo master locations for WH01
        demo_locations = [
            ("SKU001", "Organic Bananas", "Aisle_A-Bay_04-Shelf_2"),
            ("SKU002", "Farm Eggs (12)", "Aisle_A-Bay_04-Shelf_10"),
            ("SKU003", "Whole Milk 1L", "Aisle_A-Bay_01-Shelf_1"),
            ("SKU004", "Baby Spinach", "Aisle_B-Bay_02-Shelf_3"),
            ("SKU005", "Tomatoes 1kg", "Aisle_A-Bay_04-Shelf_1"),
        ]
        for sku, item_name, loc in demo_locations:
            exists = (
                db.query(MasterLocation)
                .filter(MasterLocation.warehouse_id == wh01.id, MasterLocation.item_sku == sku)
                .first()
            )
            if not exists:
                db.add(MasterLocation(warehouse_id=wh01.id, item_sku=sku, item_name=item_name, location=loc))
        db.commit()
        print("Seed complete.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
