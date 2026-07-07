# Everfresh Poultry — How It Works

A user + developer guide to the inventory and POS system. For deploying it, see
[deployment.md](deployment.md). For the original build spec, see `claude.md` in
the repo root.

---

## 1. The big picture

One Django backend serves two front-of-house experiences from a single React app:

```
Farm / Supplier ──► Lot arrival ──► Processing ──► Warehouse stock
                                                       │ transfer
                                                       ▼
Customer ◄── POS sale ◄── Outlet stock ◄── Transfer receipt
```

Four ideas drive everything:

1. **Stock is a ledger, not a number.** Every change is an append-only
   `StockMovement` row (positive = stock in, negative = stock out). Current
   stock = the SUM of those rows per (product, location). Nothing is ever
   edited or deleted — corrections are new reversing rows.
2. **Money is integer paisa.** `Rs 750.00` is stored as `75000`. The UI
   converts at the edge (`formatMoney`, `Math.round(rs * 100)`).
3. **Prices are dated rows.** A price change inserts a new `Price` row; the
   old one gets a `valid_to`. Order lines reference the exact price row used,
   so historical orders keep their original price forever.
4. **Roles are enforced at the API**, not just hidden in the UI. A cashier
   gets HTTP 403 from finance endpoints even with a hand-crafted request.

Dates display in **Bikram Sambat (BS)**; storage is Gregorian/UTC.

---

## 2. The demo data (why you see "dummy data")

`scripts/seed_data.py` populates a realistic demo environment — that is the
data you noticed. Safe to re-run (idempotent). It creates:

- 12 Everfresh outlets + Central Warehouse (Balaju) + Processing Plant
- 23 products with retail/wholesale prices
- Suppliers, wholesale/retail customers
- One user per role, per outlet

| Username | Password | Role |
|---|---|---|
| `admin` | `admin123` | Superuser |
| `om_baneshwor` … `om_boudha` | `pass1234` | Outlet manager (one per outlet) |
| `cashier_baneshwor` … `cashier_boudha` | `pass1234` | Cashier (one per outlet) |
| `worker_balaju`, `worker_proc1` | `pass1234` | Warehouse worker |
| `worker_quality`, `worker_logistics` | `pass1234` | Procurement |

The `wq_*` users and "WQ Main Outlet / WQ Warehouse" locations belong to the
automated QA script (`scripts/qa_walkthrough.py`), which exercises every role
end-to-end against a live server (86 checks).

**Reset everything:** drop and recreate the database, migrate, then re-seed:

```bash
python3 manage.py flush --noinput      # wipes rows, keeps schema
python3 scripts/seed_data.py
```

---

## 3. Who lands where

Login routes each role to its home screen (`/` redirects by role):

| Role | Lands on | Can also access |
|---|---|---|
| Cashier | POS | — |
| Warehouse / Procurement | Worker portal | — |
| Manager | Admin portal | POS |
| Outlet manager | Admin portal (scoped to own outlet, read-mostly) | POS |
| Superuser | Admin portal | everything, incl. Users / Audit / Settings |

JWTs are stored in localStorage; sessions refresh automatically and the login
endpoint is rate-limited (10/min per IP in production).

---

## 4. POS (cashiers) — `/pos`

The offline-capable sales screen.

**Shift lifecycle.** Selling requires an open `CashierSession`:
- **Open Shift** — enter the opening cash float. Until then, product tiles and
  Pay are disabled.
- **Close Shift** — enter counted cash; the Z-report summarises payments by
  method (cash/card/eSewa/Khalti) for reconciliation. A session cannot be
  closed twice.

**Selling.**
- **Search box** — filters by product name or scanned barcode.
- **Product tile** — adds one unit (1 kg or 1 piece) to the cart; tap again to
  increase, or type the exact weight in the cart's qty field.
- **Cart** shows exempt/taxable subtotals and 13% VAT on taxable items.
- **Hold** — parks the cart (held orders live in the header badge); **Void**
  — clears it after a confirmation dialog.
- **Pay** — choose method, enter cash tendered (change is computed) or a
  transaction reference for digital methods, then **Confirm Payment**.

What Confirm Payment actually does, in order:
1. `POST /orders/` — creates the Order (status `pending`)
2. `POST /order-lines/` — one per cart line, each referencing the exact price row
3. `POST /payments/` — records the payment
4. `POST /orders/{id}/fulfill/` — transitions the order to `fulfilled` and
   **writes the negative sale StockMovements**. This is the step that deducts
   outlet stock, and it refuses to oversell ("Insufficient stock").

If a step fails mid-way, retrying resumes from the failed step — nothing is
charged twice. **Print Receipt** opens a thermal-format receipt.

**Offline mode.** If the network is down, the sale is queued in IndexedDB and
the header shows OFFLINE. When connectivity returns, queued orders replay
through the same four steps automatically.

---

## 5. Worker portal (warehouse/procurement) — `/worker`

Mobile-first forms for floor staff:

- **Lot Arrival** — registers an incoming bird lot (code, source
  farm/supplier, live weight, bird count). Creates a `Lot` in `arrival` state.
- **Processing Entry** — records a slaughter/processing run against a lot:
  input vs output weight (wastage is the difference, shown live). The
  operator and timestamp are stamped server-side.
- **Receive Transfer** — lists transfers dispatched to your location; **Confirm
  Receipt** writes the transfer-in StockMovement that adds outlet stock. A
  transfer cannot be received twice.
- **Wastage** — records spoilage/damage. Quantities are stored as negative
  movements so stock decreases; the acting user is stamped server-side.
- **Flock Log** — Phase 2 placeholder (feed/mortality logging). Clearly marked;
  it saves nothing yet.

---

## 6. Admin portal (managers) — `/admin`

- **Dashboard** — recent orders with real status badges, revenue over the
  latest page of orders. (A true "today" KPI and low-stock feed are Phase 2 —
  the backend has no date-filtered aggregate endpoint yet.)
- **Products** — add or edit products (name, barcode, kg/piece, tax class);
  **+ Price** inserts a new dated price row (BS date input) for
  retail/wholesale/member tiers. Old prices are never edited.
- **Inventory** — the movement ledger, filterable by product/location, plus a
  current-stock query.
- **Transfers** — **Dispatch** (warehouse → outlet, writes transfer-out) and
  per-row **Confirm receipt** (writes transfer-in).
- **Lots** — register lots and follow their lifecycle
  (arrival → grading → storage → slaughter → packaging → sale → settlement).
- **Processing** — read-only history of processing runs.
- **Procurement** — create purchase orders against suppliers
  (draft → sent → received / cancelled).
- **Customers** — retail/wholesale customer registry (PAN for B2B invoices).
- **Invoices** — tax invoices with exempt/taxable/VAT split and CBMS (IRD)
  sync status; **Print** renders an IRD-format tax invoice. Invoices are
  immutable — corrections go through credit notes.
- **Sales Reports** — order listing with pagination, scoped to the outlet for
  outlet managers.
- **Users** (superuser) — create staff accounts with role and outlet assignment.
- **Audit Log** (superuser) — who did what, when.
- **Settings** (superuser) — read-only preview; the settings backend is Phase 2.

Every list screen shows skeleton loaders, an explicit error banner with Retry
when a fetch fails, and an empty state. Mutations confirm with a toast.

---

## 7. Behind the scenes

- **Order → Invoice.** Invoices are optional and generated only when a tax
  invoice is needed; the invoice snapshots each line's tax class and splits
  exempt vs 13% taxable amounts.
- **Celery jobs** (see `config/settings/base.py`): hourly low-stock alert,
  daily lot-expiry alert, nightly sales rollup (00:15 NPT), CBMS invoice sync
  every 15 min (stub — sets `cbms_status`).
- **Recall tracing.** Every StockMovement carries the `lot_id`, so a lot can
  be traced from arrival through to which locations sold it.
- **Health.** `GET /api/health/` reports DB + Redis status (used by container
  healthchecks and monitoring).

## 8. Known Phase 2 gaps

| Where | Gap |
|---|---|
| Worker → Flock Log | No backend endpoint yet; screen is a labeled placeholder |
| Admin → Settings | Read-only preview; no settings API |
| Admin → Dashboard | "Low Stock" card and true today-KPIs need an aggregate endpoint |
| Billing | CBMS/IRD sync is stubbed (`cbms_status` only) |
| Lots | Cost allocation across split products (`accumulated_cost_paisa`) is stubbed |

## 9. Running QA yourself

```bash
python3 -m pytest                      # 146 backend unit/integration tests
python3 scripts/qa_walkthrough.py      # 86 live API checks across all roles
cd frontend && npm run build           # production build must be clean
```

The `frontend-reviewer` Claude agent audits React screens against the API
contract (money/date formatting, role scoping, no invented fields) — run it
after any frontend change.
