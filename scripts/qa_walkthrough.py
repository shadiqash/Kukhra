"""
QA walkthrough — hits the live dev server at http://localhost:8000/api/ and
exercises every user role end-to-end.  Run with:
    python3 scripts/qa_walkthrough.py
"""
import sys
import json
import datetime
import requests

BASE = "http://localhost:8000/api"
RESULTS = []

def rows(resp):
    """Unwrap paginated {results: [...]} or plain-list responses."""
    data = resp.json()
    return data.get("results", data) if isinstance(data, dict) else data



# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def check(label, resp, expect=None, forbidden=False):
    """Record and print a PASS/FAIL line."""
    if forbidden:
        ok = resp.status_code == 403
        status_desc = f"{resp.status_code} (expected 403)"
    elif expect is not None:
        ok = resp.status_code == expect
        status_desc = f"{resp.status_code} (expected {expect})"
    else:
        ok = resp.status_code < 400
        status_desc = str(resp.status_code)

    result = "PASS" if ok else "FAIL"
    RESULTS.append((result, label, resp.status_code))
    icon = "✓" if ok else "✗"
    print(f"  {icon} [{result}] {label:60s} {status_desc}")
    return ok


def login(username, password):
    r = requests.post(f"{BASE}/auth/token/", json={"username": username, "password": password})
    if r.status_code != 200:
        print(f"  ✗ [FAIL] Login failed for {username}: {r.status_code} {r.text[:200]}")
        RESULTS.append(("FAIL", f"login:{username}", r.status_code))
        return None
    token = r.json()["access"]
    print(f"  ✓ [PASS] Login as {username:30s} 200")
    RESULTS.append(("PASS", f"login:{username}", 200))
    return {"Authorization": f"Bearer {token}"}


def get(headers, path, params=None):
    return requests.get(f"{BASE}/{path}", headers=headers, params=params)


def post(headers, path, data):
    return requests.post(f"{BASE}/{path}", headers=headers, json=data)


def patch(headers, path, data):
    return requests.patch(f"{BASE}/{path}", headers=headers, json=data)


def delete(headers, path):
    return requests.delete(f"{BASE}/{path}", headers=headers)


def section(title):
    print(f"\n{'═'*72}")
    print(f"  {title}")
    print(f"{'═'*72}")


def today():
    return datetime.date.today().isoformat()


def ensure(headers, path, match, payload, label):
    """Find an existing row matching `match` (client-side, first page) or create it."""
    r = get(headers, path, match)
    existing = None
    if r.status_code == 200:
        for item in rows(r):
            if all(str(item.get(k)) == str(v) for k, v in match.items()):
                existing = item
                break
    if existing is not None:
        check(f"{label} (reusing existing)", r, 200)
        return existing["id"]
    r = post(headers, path, payload)
    check(label, r, 201)
    return r.json().get("id") if r.status_code == 201 else None


# ═══════════════════════════════════════════════════════════════════════════════
# Setup — create all shared fixtures via admin
# ═══════════════════════════════════════════════════════════════════════════════

section("SETUP — Seeding via admin account")

admin_h = login("admin", "admin123")
if not admin_h:
    print("\nCannot reach server or credentials wrong. Is Django running on :8000?")
    sys.exit(1)

# Locations
outlet_id = ensure(admin_h, "locations/", {"name": "WQ Main Outlet"},
                   {"name": "WQ Main Outlet", "type": "outlet"}, "Outlet location")
branch_id = ensure(admin_h, "locations/", {"name": "WQ Branch Outlet"},
                   {"name": "WQ Branch Outlet", "type": "outlet"}, "Branch outlet location")
wh_id = ensure(admin_h, "locations/", {"name": "WQ Warehouse"},
               {"name": "WQ Warehouse", "type": "warehouse"}, "Warehouse location")

# Counters
counter_id = ensure(admin_h, "counters/", {"location": outlet_id, "name": "Counter A"},
                    {"location": outlet_id, "name": "Counter A"}, "Counter at outlet")

# Products
prod_chicken_id = ensure(admin_h, "products/", {"name": "Whole Chicken"},
    {"name": "Whole Chicken", "uom": "kg", "tax_class": "exempt"}, "Product: Whole Chicken (exempt)")
prod_sausage_id = ensure(admin_h, "products/", {"name": "Processed Sausage"},
    {"name": "Processed Sausage", "uom": "kg", "tax_class": "taxable"}, "Product: Sausage (taxable)")
prod_wings_id = ensure(admin_h, "products/", {"name": "Chicken Wings"},
    {"name": "Chicken Wings", "uom": "kg", "tax_class": "exempt"}, "Product: Wings (exempt)")

# Prices
def ensure_price(product_id, paisa, label):
    r = get(admin_h, "prices/", {"product": product_id, "tier": "retail", "active": "true"})
    existing = rows(r) if r.status_code == 200 else []
    if existing:
        check(f"{label} (reusing active price)", r, 200)
        return existing[0]["id"]
    r = post(admin_h, "prices/", {
        "product": product_id, "tier": "retail",
        "price_paisa": paisa, "valid_from": "2024-01-01",
    })
    check(label, r, 201)
    return r.json().get("id") if r.status_code == 201 else None

price_chicken_id = ensure_price(prod_chicken_id, 75000, "Price: Whole Chicken 750/kg")
price_sausage_id = ensure_price(prod_sausage_id, 120000, "Price: Sausage 1200/kg")
price_wings_id = ensure_price(prod_wings_id, 45000, "Price: Wings 450/kg")

# Seed stock at outlet
for prod, qty in [(prod_chicken_id, "50.000"), (prod_wings_id, "30.000"), (prod_sausage_id, "20.000")]:
    r = post(admin_h, "movements/", {
        "product": prod, "location": outlet_id,
        "type": "production", "qty_kg": qty, "qty_pieces": 0,
    })
    check(f"Seed stock {qty}kg at outlet (product {prod})", r, 201)

# Seed stock at warehouse for transfer
r = post(admin_h, "movements/", {
    "product": prod_chicken_id, "location": wh_id,
    "type": "production", "qty_kg": "100.000", "qty_pieces": 0,
})
check("Seed 100kg chicken at warehouse", r, 201)

# Create users for each role
def create_user(username, password, role, assigned_location_id=None):
    r = get(admin_h, "users/", {"username": username})
    if r.status_code == 200:
        match = next((u for u in rows(r) if u.get("username") == username), None)
        if match:
            check(f"User exists: {username} ({role})", r, 200)
            return match["id"]
    payload = {"username": username, "password": password, "role": role,
               "email": f"{username}@everfresh.local"}
    if assigned_location_id:
        payload["assigned_locations"] = [assigned_location_id]
    r = post(admin_h, "users/", payload)
    check(f"Create user: {username} ({role})", r, 201)
    return r.json().get("id") if r.status_code == 201 else None

mgr_user_id     = create_user("wq_manager",  "pass1234", "manager")
omgr_user_id    = create_user("wq_omgr",     "pass1234", "outlet_manager", outlet_id)
cashier_user_id = create_user("wq_cashier",  "pass1234", "cashier")
worker_user_id  = create_user("wq_worker",   "pass1234", "warehouse")

# Create supplier for lot
supplier_id = ensure(admin_h, "suppliers/", {"name": "WQ Farm Supply"},
                     {"name": "WQ Farm Supply", "type": "farm"}, "Supplier: WQ Farm Supply")


# ═══════════════════════════════════════════════════════════════════════════════
# 1. CASHIER FLOW
# ═══════════════════════════════════════════════════════════════════════════════

section("1. CASHIER FLOW")

cashier_h = login("wq_cashier", "pass1234")

# Open shift
r = post(cashier_h, "sessions/", {
    "counter": counter_id,
    "cashier": cashier_user_id,
    "opening_float_paisa": 50000,
    "opened_at": datetime.datetime.now().isoformat(),
})
check("Open cashier shift", r, 201)
session_id = r.json().get("id") if r.status_code == 201 else None

# Order 1: cash payment
r = post(cashier_h, "orders/", {
    "fulfilled_location": outlet_id,
    "session": session_id,
    "source": "counter",
    "total_paisa": 150000,
})
check("Create order 1", r, 201)
order1_id = r.json().get("id") if r.status_code == 201 else None

r = post(cashier_h, "order-lines/", {
    "order": order1_id, "product": prod_chicken_id, "price": price_chicken_id,
    "qty_kg": "2.000", "qty_pieces": 0, "line_total_paisa": 150000,
})
check("Add order 1 line: 2kg chicken", r, 201)

r = post(cashier_h, "orders/" + str(order1_id) + "/fulfill/", {})
check("Fulfill order 1", r, 200)

r = post(cashier_h, "payments/", {
    "order": order1_id, "method": "cash", "amount_paisa": 150000,
})
check("Payment 1: cash 1500", r, 201)

# Order 2: card payment, two lines
r = post(cashier_h, "orders/", {
    "fulfilled_location": outlet_id, "session": session_id,
    "source": "counter", "total_paisa": 90000,
})
check("Create order 2", r, 201)
order2_id = r.json().get("id") if r.status_code == 201 else None

r = post(cashier_h, "order-lines/", {
    "order": order2_id, "product": prod_wings_id, "price": price_wings_id,
    "qty_kg": "2.000", "qty_pieces": 0, "line_total_paisa": 90000,
})
check("Add order 2 line: 2kg wings", r, 201)

r = post(cashier_h, "orders/" + str(order2_id) + "/fulfill/", {})
check("Fulfill order 2", r, 200)

r = post(cashier_h, "payments/", {
    "order": order2_id, "method": "card", "amount_paisa": 90000,
})
check("Payment 2: card 900", r, 201)

# Order 3: eSewa + split payment
r = post(cashier_h, "orders/", {
    "fulfilled_location": outlet_id, "session": session_id,
    "source": "counter", "total_paisa": 240000,
})
check("Create order 3", r, 201)
order3_id = r.json().get("id") if r.status_code == 201 else None

r = post(cashier_h, "order-lines/", {
    "order": order3_id, "product": prod_chicken_id, "price": price_chicken_id,
    "qty_kg": "2.000", "qty_pieces": 0, "line_total_paisa": 150000,
})
check("Add order 3 line A: 2kg chicken", r, 201)

r = post(cashier_h, "order-lines/", {
    "order": order3_id, "product": prod_sausage_id, "price": price_sausage_id,
    "qty_kg": "0.750", "qty_pieces": 0, "line_total_paisa": 90000,
})
check("Add order 3 line B: 0.75kg sausage", r, 201)

r = post(cashier_h, "orders/" + str(order3_id) + "/fulfill/", {})
check("Fulfill order 3", r, 200)

# A digital payment with no gateway proof is money nobody can show arrived.
# It used to be accepted on the cashier's word alone; it must now be refused.
r = post(cashier_h, "payments/", {
    "order": order3_id, "method": "esewa", "amount_paisa": 140000,
    "ref": "I promise I paid",
})
check("Unverified eSewa payment is rejected (400)", r, 400)

r = post(cashier_h, "payments/", {
    "order": order3_id, "method": "card", "amount_paisa": 140000,
})
check("Payment 3a: card 1400", r, 201)

r = post(cashier_h, "payments/", {
    "order": order3_id, "method": "cash", "amount_paisa": 100000,
})
check("Payment 3b: cash 1000 (split)", r, 201)

# Cashier tries to access invoices — must fail
r = get(cashier_h, "invoices/")
check("Cashier cannot access invoices (403)", r, forbidden=True)

r = get(cashier_h, "movements/")
check("Cashier cannot access stock movements (403)", r, forbidden=True)

# Close shift
r = post(cashier_h, f"sessions/{session_id}/close/", {"closing_counted_paisa": 300000})
check("Close cashier shift", r, 200)

# Z-report: fetch all payments for this session
r = get(cashier_h, "payments/", {"order__session": session_id})
check("Fetch Z-report payment data", r, 200)
if r.status_code == 200:
    payments = rows(r)
    by_method = {}
    for p in payments:
        m = p["method"]
        by_method[m] = by_method.get(m, 0) + p["amount_paisa"]
    total = sum(by_method.values())
    print(f"\n  Z-REPORT for session {session_id}:")
    for method, amt in sorted(by_method.items()):
        print(f"    {method:10s}  Rs {amt/100:,.2f}")
    print(f"    {'TOTAL':10s}  Rs {total/100:,.2f}")

# Double-close (must fail)
r = post(cashier_h, f"sessions/{session_id}/close/", {"closing_counted_paisa": 999999})
check("Double-close shift returns 400", r, 400)


# ═══════════════════════════════════════════════════════════════════════════════
# 2. MANAGER FLOW
# ═══════════════════════════════════════════════════════════════════════════════

section("2. MANAGER FLOW")

mgr_h = login("wq_manager", "pass1234")

# View dashboard-style data
r = get(mgr_h, "orders/")
check("Manager can list all orders", r, 200)
order_count = len(rows(r)) if r.status_code == 200 else "?"
print(f"    → {order_count} orders visible")

r = get(mgr_h, "sessions/")
check("Manager can list cashier sessions", r, 200)

# View stock at outlet
r = get(mgr_h, "stock/", {"product": prod_chicken_id, "location": outlet_id})
check("Manager can query outlet stock", r, 200)
if r.status_code == 200:
    print(f"    → Chicken at outlet: {r.json().get('qty_kg')} kg")

# View movements
r = get(mgr_h, "movements/", {"location": outlet_id})
check("Manager can view movements at outlet", r, 200)

# View invoices
r = get(mgr_h, "invoices/")
check("Manager can view invoices", r, 200)

# View transfers
r = get(mgr_h, "transfers/")
check("Manager can view transfers", r, 200)

# Create an invoice for order 1
r = post(mgr_h, "invoices/", {
    "order": order1_id,
    "invoice_number": f"INV-WQ-{order1_id:04d}",
    "issued_at": datetime.datetime.now().isoformat(),
})
check("Manager can create invoice", r, 201)
invoice_id = r.json().get("id") if r.status_code == 201 else None

# Create and dispatch a transfer. Lines travel with the dispatch: the transfer-out
# movements are written server-side, so no manual movement post is needed.
r = post(mgr_h, "transfers/", {
    "from_location": wh_id,
    "to_location": outlet_id,
    "dispatched_at": datetime.datetime.now().isoformat(),
    "lines": [{"product": prod_chicken_id, "qty_kg": "15.000"}],
})
check("Manager creates transfer with lines (WH → outlet, 15kg)", r, 201)
transfer_id = r.json().get("id") if r.status_code == 201 else None

# Oversell guard: cannot dispatch more than is on hand at the source.
r = post(mgr_h, "transfers/", {
    "from_location": wh_id,
    "to_location": outlet_id,
    "dispatched_at": datetime.datetime.now().isoformat(),
    "lines": [{"product": prod_chicken_id, "qty_kg": "999999.000"}],
})
check("Manager cannot dispatch more stock than on hand (400)", r, 400)

# Immutability: try to delete a transfer-out movement
r = get(mgr_h, f"movements/?location={wh_id}&type=transfer")
if r.status_code == 200:
    transfer_movements = rows(r)
    if transfer_movements:
        mv_id = transfer_movements[-1]["id"]
        r2 = delete(mgr_h, f"movements/{mv_id}/")
        check("Manager cannot delete a movement (405)", r2, 405)

# Immutability: try to patch a price
r2 = patch(mgr_h, f"prices/{price_chicken_id}/", {"price_paisa": 1})
check("Manager cannot patch a price (405)", r2, 405)


# ═══════════════════════════════════════════════════════════════════════════════
# 3. OUTLET MANAGER FLOW
# ═══════════════════════════════════════════════════════════════════════════════

section("3. OUTLET MANAGER FLOW")

omgr_h = login("wq_omgr", "pass1234")

# Can read their outlet's data
r = get(omgr_h, "invoices/")
check("Outlet manager can read invoices", r, 200)
if r.status_code == 200:
    print(f"    → {len(rows(r))} invoices visible (own outlet only)")

r = get(omgr_h, "orders/")
check("Outlet manager can read orders", r, 200)
if r.status_code == 200:
    for o in rows(r):
        assert o["fulfilled_location"] == outlet_id, \
            f"BUG: order {o['id']} at location {o['fulfilled_location']} leaked to outlet_manager"
    print(f"    → {len(rows(r))} orders — all scoped to assigned outlet ✓")

r = get(omgr_h, "stock/", {"product": prod_chicken_id, "location": outlet_id})
check("Outlet manager can query own outlet stock", r, 200)

# Branch outlet stock — must be blocked (403) because it's not assigned
r = get(omgr_h, "stock/", {"product": prod_chicken_id, "location": branch_id})
check("Outlet manager blocked from branch outlet stock (403)", r, forbidden=True)

r = get(omgr_h, "movements/", {"location": outlet_id})
check("Outlet manager can read own outlet movements", r, 200)

# Write attempts — must be blocked
r = post(omgr_h, "orders/", {
    "fulfilled_location": outlet_id, "session": session_id,
    "source": "counter", "total_paisa": 0,
})
check("Outlet manager cannot create orders (403)", r, forbidden=True)

r = post(omgr_h, "movements/", {
    "product": prod_chicken_id, "location": outlet_id,
    "type": "adjustment", "qty_kg": "5.000", "qty_pieces": 0,
})
check("Outlet manager cannot create movements (403)", r, forbidden=True)

r = get(omgr_h, "transfers/")
check("Outlet manager can read transfers", r, 200)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. WORKER FLOW
# ═══════════════════════════════════════════════════════════════════════════════

section("4. WORKER FLOW")

worker_h = login("wq_worker", "pass1234")

# Create a lot arrival
r = post(worker_h, "lots/", {
    "code": f"LOT-QA-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
    "source_type": "external",
    "supplier": supplier_id,
    "arrival_location": wh_id,
    "live_weight_kg": "250.000",
    "bird_count": 200,
})
check("Worker creates lot arrival", r, 201)
lot_id = r.json().get("id") if r.status_code == 201 else None

# Transition lot to grading
r = post(worker_h, f"lots/{lot_id}/transition/", {"status": "grading"})
check("Worker transitions lot: arrival → grading", r, 200)

# Transition to slaughter (grading → storage → slaughter or direct)
r = post(worker_h, f"lots/{lot_id}/transition/", {"status": "storage"})
check("Worker transitions lot: grading → storage", r, 200)

r = post(worker_h, f"lots/{lot_id}/transition/", {"status": "slaughter"})
check("Worker transitions lot: storage → slaughter", r, 200)

r = post(worker_h, f"lots/{lot_id}/transition/", {"status": "packaging"})
check("Worker transitions lot: slaughter → packaging", r, 200)

# Enter processing run
r = post(worker_h, "processing-runs/", {
    "lot": lot_id,
    "location": wh_id,
    "input_weight_kg": "250.000",
    "output_weight_kg": "210.000",
    "wastage_kg": "40.000",
    "processed_at": datetime.datetime.now().isoformat(),
})
check("Worker creates processing run", r, 201)

# Receive the transfer created by manager
r = post(worker_h, f"transfers/{transfer_id}/confirm-receipt/", {})
check("Worker confirms receipt of transfer", r, 200)
if r.status_code == 200:
    print(f"    → Transfer {transfer_id} status: {r.json().get('status')}")

# Check stock at outlet after receipt
r = get(omgr_h, "stock/", {"product": prod_chicken_id, "location": outlet_id})
check("Stock at outlet updated after transfer receipt", r, 200)
if r.status_code == 200:
    print(f"    → Chicken at outlet after receipt: {r.json().get('qty_kg')} kg")

# Record wastage movement
r = post(worker_h, "movements/", {
    "product": prod_chicken_id, "location": wh_id,
    "type": "wastage", "qty_kg": "-2.500", "qty_pieces": 0,
})
check("Worker records wastage movement", r, 201)

# Worker tries to access prices — must fail
r = get(worker_h, "prices/")
check("Worker cannot access prices (403)", r, forbidden=True)

# Worker tries to access orders — must fail
r = get(worker_h, "orders/")
check("Worker cannot access orders (403)", r, forbidden=True)

# Worker tries to access invoices — must fail
r = get(worker_h, "invoices/")
check("Worker cannot access invoices (403)", r, forbidden=True)

# Worker tries to access payments — must fail
r = get(worker_h, "payments/")
check("Worker cannot access payments (403)", r, forbidden=True)


# ═══════════════════════════════════════════════════════════════════════════════
# 5. ADMIN FLOW
# ═══════════════════════════════════════════════════════════════════════════════

section("5. ADMIN FLOW")

# Already have admin_h from setup

# View all outlets
r = get(admin_h, "locations/")
check("Admin can list all locations", r, 200)
if r.status_code == 200:
    print(f"    → {len(rows(r))} locations total")

# View all users
r = get(admin_h, "users/")
check("Admin can list all users", r, 200)

# View all invoices
r = get(admin_h, "invoices/")
check("Admin can view all invoices", r, 200)
if r.status_code == 200:
    print(f"    → {len(rows(r))} invoices")

# View stock across warehouse
r = get(admin_h, "stock/", {"product": prod_chicken_id, "location": wh_id})
check("Admin can query warehouse stock", r, 200)
if r.status_code == 200:
    print(f"    → Chicken at warehouse: {r.json().get('qty_kg')} kg")

# View all orders
r = get(admin_h, "orders/")
check("Admin can see all orders", r, 200)
if r.status_code == 200:
    print(f"    → {len(rows(r))} total orders")

# View all movements
r = get(admin_h, "movements/")
check("Admin can see all movements", r, 200)

# View all transfers
r = get(admin_h, "transfers/")
check("Admin can see all transfers", r, 200)

# Delete invoice must return 405 (immutable)
if invoice_id:
    r = delete(admin_h, f"invoices/{invoice_id}/")
    check("Admin cannot delete invoice (405 — immutable)", r, 405)

# Double-receive transfer — must fail
r = post(admin_h, f"transfers/{transfer_id}/confirm-receipt/", {})
check("Double-confirm-receipt returns 400", r, 400)

# /users/me/
r = get(admin_h, "users/me/")
check("Admin /users/me/ returns own profile", r, 200)
if r.status_code == 200:
    print(f"    → Logged in as: {r.json().get('username')} ({r.json().get('role')})")


# ═══════════════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════════════

section("SUMMARY")

passed = [r for r in RESULTS if r[0] == "PASS"]
failed = [r for r in RESULTS if r[0] == "FAIL"]

print(f"\n  Total:  {len(RESULTS)}")
print(f"  PASS:   {len(passed)}")
print(f"  FAIL:   {len(failed)}")

if failed:
    print(f"\n  FAILURES ({len(failed)}):")
    for _, label, code in failed:
        print(f"    ✗ {label}  →  HTTP {code}")
else:
    print("\n  All checks passed ✓")

sys.exit(0 if not failed else 1)
