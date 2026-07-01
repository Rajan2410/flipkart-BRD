"""End-to-end flow test against an isolated temp SQLite DB."""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

# Point DB at a temp file BEFORE importing app modules.
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"

from app.main import app  # noqa: E402
from app.seed import seed  # noqa: E402

seed()
client = TestClient(app)

V1 = "/api/v1"


def _token(username: str, password: str) -> str:
    r = client.post(f"{V1}/auth/login", data={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_health():
    assert client.get("/health").json()["status"] == "ok"


def test_full_flow():
    admin = _token("admin", "admin123")

    # Ingest orders (master locations already seeded for WH01)
    with open("sample_data/orders.csv", "rb") as f:
        r = client.post(f"{V1}/orders/ingest", headers=_h(admin), files={"file": ("orders.csv", f, "text/csv")})
    assert r.status_code == 200, r.text
    assert r.json()["orders_created"] == 2

    # Picker enters WH01
    wh = client.get(f"{V1}/admin/warehouses", headers=_h(admin)).json()
    wh01_id = next(w["id"] for w in wh if w["code"] == "WH01")

    picker = _token("picker1", "picker123")
    r = client.post(f"{V1}/picking/enter-warehouse", headers=_h(picker), json={"warehouse_id": wh01_id})
    assert r.status_code == 200, r.text

    # Queue -> claim first order
    queue = client.get(f"{V1}/picking/queue", headers=_h(picker)).json()
    assert len(queue) == 2
    order_id = "ORD1001"
    r = client.post(f"{V1}/picking/orders/{order_id}/claim", headers=_h(picker))
    assert r.status_code == 200, r.text
    lines = r.json()["lines"]

    # Verify walk-path ordering: Tomatoes(Shelf_1) -> Bananas(Shelf_2) -> Eggs(Shelf_10)
    assert [ln["item_sku"] for ln in lines] == ["SKU005", "SKU001", "SKU002"]

    # Wrong scan is rejected (Bananas not the active step; Tomatoes is)
    r = client.post(f"{V1}/picking/orders/{order_id}/scan", headers=_h(picker), json={"item_sku": "SKU001"})
    assert r.status_code == 409

    # Scan the full order in the correct sequence
    for sku, qty in [("SKU005", 2), ("SKU001", 3), ("SKU002", 1)]:
        for _ in range(qty):
            r = client.post(f"{V1}/picking/orders/{order_id}/scan", headers=_h(picker), json={"item_sku": sku})
            assert r.status_code == 200, r.text
    assert r.json()["order_completed"] is True

    # Dispatch report reflects 100% fulfillment for ORD1001
    r = client.get(f"{V1}/reports/dispatch?warehouse_id={wh01_id}", headers=_h(admin))
    assert r.status_code == 200
    body = r.text
    assert "Fulfillment_Rate" in body
    for line in body.splitlines():
        if line.startswith("ORD1001"):
            assert line.strip().endswith("100.0")


def test_picker_cannot_reach_admin_routes():
    picker = _token("picker1", "picker123")
    r = client.get(f"{V1}/admin/users", headers=_h(picker))
    assert r.status_code == 403
