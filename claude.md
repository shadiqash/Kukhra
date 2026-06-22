# Everfresh Poultry — Phase 1 Build Spec

> Build spec for Claude Code. Read this fully before writing any code. Build in the order given in **Build sequence**. Do not skip ahead.

## What we are building

A single backend serving an **inventory system** and an **outlet billing (POS) system** for a chicken business: production → warehouse → 12 retail outlets → customer, plus sales to outside wholesale shops.

The customer mobile app, online ordering, nearest-outlet routing, loyalty, full accounting, and delivery tracking are **Phase 2 — out of scope now.** Leave room for them but do not build them.

## Tech stack (fixed)

- Backend: **Django + Django REST Framework**
- Database: **PostgreSQL**
- Async: **Celery + Redis**
- Frontend: **React + Tailwind** (web; offline-capable POS screen)
- Auth: JWT, role-scoped

## Non-negotiable design rules

These are foundational. Getting them wrong is expensive to undo. Follow them everywhere.

1. **Append-only ledgers.** Stock is never stored as a mutable balance. Every change is a new `StockMovement` row. Current stock = SUM of movements for a (product, location). Corrections are reversing rows, never edits or deletes.
2. **Prices are dated rows, never a field on the product.** A price change inserts a new `Price` row with `valid_from`/`valid_to`. Sales reference the exact `price_id` used, so old orders keep their original price.
3. **All money is integer paisa.** Never use float for money anywhere.
4. **Location is first-class.** Stock is always per-location. Never assume a single location.
5. **`lot_id` rides on every `StockMovement`** so recall tracing works by querying movements. (Shallow recall: trace lot → location is enough. Lot identity ends at processing output; mince/kebab become their own production batches, not traced per-lot.)
6. **Order is the single entry point for all sales** (counter / phone / wholesale). `Invoice` is optional on an order — only generated when a tax invoice is needed.
7. **Role enforcement is at the API**, not just the UI. A cashier role must have *no* finance/billing-report endpoints available, not merely hidden.

## Django apps

```
core         # BS-calendar utils, money (paisa) helpers, UoM conversion, base models, audit mixin
accounts     # users, roles/RBAC, audit log
locations    # Location, Counter
partners     # Supplier, Customer
catalog      # Product, Price
lots         # Lot, lifecycle state machine
processing   # ProcessingRun
inventory    # StockMovement, StockTransfer
procurement  # PurchaseOrder, GoodsReceived
sales        # CashierSession, Order, OrderLine, Payment
billing      # Invoice, InvoiceLine, CreditNote
```

## Database schema (18 tables)

All tables have `id` PK. All money fields are integer paisa. Use Django models; generate migrations.

### locations
- **Location**: name, type (`farm|production|warehouse|outlet`), lat (decimal, null), lng (decimal, null)
- **Counter**: location (FK), name

### partners
- **Supplier**: name, type (`farm|feed|medicine`), pan (null)
- **Customer**: name, type (`retail|wholesale`), pan (null), credit_limit_paisa (default 0), lat (null), lng (null)

### catalog
- **Product**: name, barcode (null), uom (`kg|piece`), is_weighed (bool), tax_class (`exempt|taxable`, default exempt — confirm per product later)
- **Price**: product (FK), tier (`retail|wholesale|member`), price_paisa (int), valid_from (date), valid_to (date, null = current)

### lots
- **Lot**: code (unique), source_type (`own|external`), supplier (FK null), arrival_location (FK), live_weight_kg (decimal), bird_count (int), accumulated_cost_paisa (int, default 0), status (`arrival|grading|storage|slaughter|packaging|sale|settlement`)

### processing
- **ProcessingRun**: lot (FK), run_at (datetime), input_weight_kg (decimal), output_weight_kg (decimal), operator (FK user)

### inventory
- **StockMovement** (append-only; never update/delete): product (FK), location (FK), lot (FK null), type (`production|transfer|sale|return|wastage|adjustment`), qty_kg (decimal, default 0), qty_pieces (int, default 0), ref_id (int null), user (FK), created_at (datetime auto)
- **StockTransfer**: from_location (FK), to_location (FK), status (`dispatched|received`), dispatched_at (datetime). A confirmed transfer creates two StockMovements (transfer-out, transfer-in).

### procurement
- **PurchaseOrder**: supplier (FK), status, total_paisa (int)
- **GoodsReceived**: purchase_order (FK), location (FK), received_at (datetime). Receiving creates StockMovements (type=production/transfer as appropriate) and/or a Lot for bird purchases.

### sales
- **CashierSession**: counter (FK), cashier (FK user), opening_float_paisa (int), closing_counted_paisa (int null), opened_at (datetime), closed_at (datetime null)
- **Order**: customer (FK null), fulfilled_location (FK), session (FK null), source (`counter|app|phone|wholesale`), status, total_paisa (int)
- **OrderLine**: order (FK), product (FK), price (FK Price), qty_kg (decimal default 0), qty_pieces (int default 0), line_total_paisa (int)
- **Payment**: order (FK), method (`cash|card|esewa|khalti`), amount_paisa (int), ref (text null)

### billing
- **Invoice**: order (FK), invoice_no (unique), taxable_paisa (int), exempt_paisa (int), vat_paisa (int), cbms_status (default `pending`), issued_at (datetime)
- **InvoiceLine**: invoice (FK), product (FK), tax_class (snapshot text), amount_paisa (int), vat_paisa (int)
- **CreditNote**: invoice (FK), amount_paisa (int), reason (text), cbms_status (default `pending`)

## Event write-rules (how rows are created)

- **Lot arrival** → create Lot.
- **Processing run** → create ProcessingRun; for each output product create a StockMovement(type=production, location=production/warehouse, lot=source lot, qty).
- **Transfer warehouse→outlet** → create StockTransfer; on dispatch a transfer-out movement, on receive a transfer-in movement.
- **Counter sale** → create Order(source=counter, fulfilled_location=outlet, session) + OrderLines (each referencing the active Price) + Payment(s); for each line create StockMovement(type=sale, location=outlet, negative qty). Generate Invoice only if required.
- **Return** → reversing StockMovement(type=return) + CreditNote if invoiced.
- **Wastage** → StockMovement(type=wastage) with reason; requires manager role.
- **Stock at a location** = `SUM(qty)` of its StockMovements (never a stored column).

## Build sequence (do in this order; commit after each)

1. Project scaffold: Django project, the apps above, DRF, Postgres settings, JWT auth.
2. `core` + `accounts`: base model, audit mixin, User, roles. Migrate.
3. `locations`, `partners`, `catalog`: master-data models + migrations + admin.
4. `lots`, `processing`: models + lot status state machine.
5. `inventory`: StockMovement + StockTransfer + a `current_stock(product, location)` query helper. **Write tests proving stock = sum of movements.**
6. `procurement`: PurchaseOrder, GoodsReceived wiring into movements.
7. `sales`: CashierSession, Order, OrderLine, Payment + the sale → movement rule.
8. `billing`: Invoice/InvoiceLine/CreditNote + tax split (exempt vs 13% taxable).
9. DRF endpoints + role scoping (cashier has no finance endpoints).
10. React: POS screen (offline-capable) + admin screens.
11. Celery: low-stock/expiry alerts, CBMS sync stub.

## Open items (do NOT hardcode; leave configurable / TODO)

- VAT registration status and which products are taxable — pending management. Default `tax_class=exempt`; make tax engine read the flag.
- Cost-allocation method when one lot splits into many products (by weight vs sales value) — pending. Stub `accumulated_cost_paisa` for now.
- CBMS/IRD real integration — stub the sync; just set `cbms_status`.

## Conventions

- Tests for every model that holds money or stock.
- No raw deletes on StockMovement/Price/Invoice — enforce at model level.
- Use Django migrations; never edit the DB by hand.
- Keep PRs/commits small and per-step.