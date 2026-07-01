# ShelfLife — Outbound Picking & Dispatch System

Backend for orchestrating and optimizing the picking of outbound fresh-produce
orders at fulfillment hubs. Central Operations ingest orders, the system maps
items to physical shelves and computes an optimized walk-path, and Hub Pickers
scan items location-by-location with a full audit trail.

FastAPI · SQLAlchemy 2.0 · SQLite · JWT (access-only).

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # optional; sensible defaults ship in code
python -m app.seed            # creates tables + bootstrap admin + demo data
uvicorn app.main:app --reload
```

Interactive docs: http://127.0.0.1:8000/docs · Health: `/health`

Seed accounts: `admin / admin123` (Central Admin), `picker1 / picker123`
(Hub Picker, mapped to WH01).

### Docker

```bash
docker build -t shelflife . && docker run -p 8000:8000 shelflife
```

## Roles (RBAC)

| Role | Capabilities |
|---|---|
| **Central Admin** | Warehouses, picker↔warehouse mapping, master shelf mapping, order ingestion, cross-warehouse reports |
| **Hub Picker** | Enter assigned warehouse, claim orders, scan-to-pick — restricted to their active warehouse only |

## Core flow

1. **Admin** creates warehouses, pickers, and the master `SKU → shelf` layout.
2. **Admin** uploads daily orders (CSV/Excel). On ingest, each line's shelf is
   resolved and lines are pre-sequenced into an optimized walk-path.
3. **Picker** enters a warehouse, claims an order (atomically locked), and scans
   items in walk-path order. Each correct scan is `+1`; wrong-location items are
   rejected until the active step is picked or skipped.
4. **Admin** downloads the dispatch report with a dynamic fulfillment rate.

`Fulfillment_Rate = (Quantity_Picked / Quantity_Ordered) × 100`

## Ingestion file formats

**Orders** — `Order_ID, Customer_ID, Warehouse_ID, Item_SKU, Item_Name, Quantity_Ordered`
**Master layout** — `Warehouse_ID, Item_SKU, Item_Name, Location`

`Warehouse_ID` is the warehouse **code** (e.g. `WH01`). Samples in `sample_data/`.

## Selected endpoints (`/api/v1`)

| Method | Path | Role | Purpose |
|---|---|---|---|
| POST | `/auth/login` | any | OAuth2 password login → JWT |
| POST | `/admin/warehouses` | admin | Create warehouse |
| POST | `/admin/users` | admin | Create picker/admin |
| PUT | `/admin/users/{id}/warehouses` | admin | Map picker → warehouses |
| POST | `/admin/locations/upload` | admin | Bulk master layout |
| POST | `/orders/ingest` | admin | Upload order file |
| POST | `/picking/enter-warehouse` | picker | Set active warehouse |
| GET | `/picking/queue` | picker | Unclaimed orders in scope |
| POST | `/picking/orders/{id}/claim` | picker | Lock an order |
| POST | `/picking/orders/{id}/scan` | picker | Scan-to-pick (+1) |
| POST | `/picking/orders/{id}/skip` | picker | Bypass active step |
| GET | `/reports/dispatch?format=csv\|xlsx` | admin | Download report |

## Design decisions & proactive refinements

- **Routing engine** uses a *natural sort* of the location identifier, so
  `Shelf_2` precedes `Shelf_10` (naive lexical sort gets this wrong). See
  `app/services/routing.py`. A true travel-distance (TSP) optimiser is a
  documented next step.
- **Master locations are scoped per warehouse**, not global — the same SKU can
  sit at different shelves across hubs.
- **Order locking** is an atomic conditional `UPDATE` (`PENDING → IN_PROGRESS`),
  safe under concurrent claims.
- **Data isolation**: out-of-scope orders return `404`, not `403`, to avoid
  leaking existence across warehouses.
- **Audit trail** records every scan, invalid scan, skip, and completion.

## Project layout

```
app/
  core/       config, database, security (jwt + bcrypt)
  models/     SQLAlchemy models + enums
  schemas/    Pydantic v2 request/response models
  services/   ingestion, routing, picking, reporting (business logic)
  api/        deps (auth guards) + routes/ (auth, admin, orders, picking, reports)
  main.py     app factory
  seed.py     bootstrap admin + demo data
tests/        end-to-end flow test
sample_data/  example CSVs
```

## Tests

```bash
pytest -q
```

## Production notes (not yet wired)

Swap `init_db()` for **Alembic** migrations; move secrets to a secret manager;
add rate-limiting on `/auth/login`; put SQLite behind PostgreSQL for
multi-writer concurrency at hub scale.
