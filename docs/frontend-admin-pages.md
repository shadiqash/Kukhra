# Everfresh Admin Portal — UI Element Inventory

Source: `frontend/src/admin/*.jsx`, cross-referenced against `frontend/src/api/index.js`.

---

## Shell / Navigation (`AdminLayout.jsx`)

**Purpose:** Provides the persistent sidebar navigation, top bar, and content outlet that every admin page renders inside.

**Layout/structure:** Fixed-width (240px) left sidebar (`bg-brand-primary`) + main content column. Sidebar has a logo/brand header, a scrollable nav list, and a user/logout footer pinned to the bottom. Main column has a top header bar (page title + date) and a scrollable content `<main>` that renders `<Outlet />` (the active page).

**Elements:**
- Logo mark (inline SVG chicken/bird icon) + "Everfresh" wordmark, static, non-interactive.
- Nav list (`NAV` array), one `NavLink` per entry, each with a lucide icon + label:
  - Dashboard (`/admin/dashboard`, `LayoutGrid` icon)
  - Products (`/admin/products`, `Package`)
  - Inventory (`/admin/inventory`, `Layers`)
  - Transfers (`/admin/transfers`, `ArrowRightLeft`)
  - Invoices (`/admin/invoices`, `Receipt`)
  - Sales Reports (`/admin/reports`, `BarChart3`)
  - Lots (`/admin/lots`, `Box`)
  - Processing (`/admin/processing`, `Scissors`)
  - Procurement (`/admin/procurement`, `Truck`)
  - Customers (`/admin/customers`, `Users`)
  - Users (`/admin/users`, `UserCog`) — **adminOnly**
  - Audit Log (`/admin/audit`, `Clock`) — **adminOnly**
  - Settings (`/admin/settings`, `Settings`) — **adminOnly**
  - Active nav item is highlighted (`bg-white/10`, bold white text) via `NavLink`'s `isActive`.
- User/role footer: text showing `"Admin" | "Manager"` (from `isAdmin()`) followed by `· {user.username}` (falls back to "admin" if no user).
- Logout button (`LogOut` icon only, `title="Sign Out"`) — calls `logout()` from `AuthContext`.
- Top bar: page title (derived by matching current path prefix against `NAV`, defaulting to "Admin Portal") and a live BS (Bikram Sambat) date string from `getTodayBS()`.
- No loading/empty/error states of its own — purely structural chrome.

**Data source:** No direct API calls. Reads `user`, `logout`, `isAdmin()` from `AuthContext` (`useAuth`), and `location` from `react-router-dom`.

**Role/access notes:** Nav items flagged `adminOnly: true` (Users, Audit Log, Settings) are filtered out of the rendered list unless `isAdmin()` returns true — i.e., non-admin (e.g., outlet_manager) users never see these three links. Footer label distinguishes "Admin" vs "Manager" generically based on `isAdmin()`, not per-specific-role.

---

## Dashboard (`Dashboard.jsx`)

**Purpose:** At-a-glance landing page summarizing recent order activity and revenue.

**Layout/structure:** 3-column KPI card row at top, followed by a two-panel row: a wide (65%) "Recent Orders" table card and a narrow (35%) "Low Stock Alerts" placeholder card.

**Elements:**
- KPI Card 1 — "Recent Revenue": shows `formatMoney(todayTotal)` (sum of `total_paisa` across fetched orders), sub-label `Latest {todayCount} orders`, `Coins` icon, green-tinted icon background.
- KPI Card 2 — "Recent Orders": shows `todayCount` as a string, sub-label "Most recent page", `ShoppingBag` icon.
- KPI Card 3 — "Low Stock": static em-dash "—" value (not wired up), sub-label "Visit Inventory to check" in secondary gray text, `AlertTriangle` icon on red-tinted background.
- Each KPI card shows a skeleton pulse block (`animate-pulse`) instead of its value while `loading` is true.
- Recent Orders table, columns: Order #, Date, Outlet, Items, Total, Status.
  - Order # → `#{o.id}` (mono font).
  - Date → `formatDateString(new Date(o.created_at))` or "—".
  - Outlet → looked up via `locationMap[o.fulfilled_location]?.name`, else "—".
  - Items → `o.lines?.length` or "—".
  - Total → `formatMoney(o.total_paisa ?? 0)`.
  - Status badge, pill-styled, color-coded:
    - `fulfilled` → green (`bg-[#dcfce7] text-brand-success`)
    - `cancelled` → red (`bg-[#fef2f2] text-brand-danger`)
    - anything else (e.g. `pending`) → amber (`bg-[#fef3c7] text-[#92400e]`)
  - Loading state: 4 skeleton rows with pulsing gray bars in each of the 6 columns.
  - Empty state: single row, "No orders yet." centered across all 6 columns.
- Low Stock Alerts panel: static placeholder only — large `AlertTriangle` icon + text "Visit the Inventory screen to check current stock levels." No live data, no loading state (always shows the same message).

**Data source:**
- `getOrders({ page: 1 })` — populates recent orders (only first 5 of whatever page 1 returns are shown: `orders.slice(0, 5)`); also computes `todayCount` and `todayTotal` from the **full** returned page (not just the 5 displayed).
- `getLocations()` — used to resolve `fulfilled_location` id → location name via `locationMap`.
- Both calls run via `Promise.allSettled`, so one failing doesn't block the other from rendering.
- Fields shown: `o.id`, `o.created_at`, `o.fulfilled_location`, `o.lines`, `o.total_paisa`, `o.status`; `l.id`, `l.name`.

**Role/access notes:** Code comment states "Outlet managers are scoped server-side to their assigned locations" — i.e., the `getOrders` call itself is not filtered client-side by role; the backend is expected to scope results for outlet managers. No client-side role branching in this file.

---

## Products (`Products.jsx`)

**Purpose:** Manage the product catalog and its retail/wholesale price records.

**Layout/structure:** Action bar (two buttons) above a single data table; two separate centered modals ("Add/Edit Product" and "Add Price") toggled by local state.

**Elements:**
- Button "+ Price" (outlined, `Plus` icon) — opens the Add Price modal (`setShowPriceModal(true)`).
- Button "+ Product" (solid brand-primary, `Plus` icon) — opens Add/Edit Product modal in "create" mode.
- `ErrorBanner` for `loadError` (product fetch failure) with `onRetry={refetch}`.
- Products table, columns: Name, Barcode, UoM, Tax, Retail Price, Wholesale Price, Action.
  - Name → `p.name`.
  - Barcode → `p.barcode` (mono) or "—".
  - UoM → `p.uom`, uppercased in display.
  - Tax badge: `exempt` → gray pill "Exempt"; anything else → amber pill "Taxable".
  - Retail Price → looked up from `prices` where `tier === 'retail'` matching `product` id, formatted via `formatMoney`; "—" if none.
  - Wholesale Price → same but `tier === 'wholesale'`; "—" if none.
  - Action → Edit icon button (`Edit2`, `aria-label="Edit {name}"`) opens the product modal pre-filled for editing.
  - Loading state: 4 skeleton rows (`LoadingRows` component), 7 pulsing cells each.
  - Empty state: "No products yet." spanning all 7 columns.
- **Add/Edit Product modal** (title toggles "Edit Product"/"Add Product" based on `editingId`):
  - Inline error text (from failed save) shown above the form.
  - Input: Name (required text).
  - Input: Barcode (optional text, placeholder "Scan or type…", mono font).
  - Select: Unit of Measure — options `kg`, `piece`.
  - Select: Tax Class — options `Exempt` (`exempt`), `Taxable (13% VAT)` (`taxable`).
  - Button "Cancel" — closes modal, resets form and `editingId`.
  - Button "Save"/"Saving…" (disabled while `saving`) — submits via `createProduct` or `updateProduct` depending on `editingId`.
- **Add Price modal**:
  - Inline error text.
  - Select: Product (required) — populated from `products`, "Select…" placeholder.
  - Select: Tier — options Retail (`retail`), Wholesale (`wholesale`), Member (`member`).
  - Input: Price (Rs) (required number, min 0, step 0.01) — converted to paisa (`Math.round(parseFloat(...) * 100)`) on submit.
  - Input: Valid From (required text, placeholder "YYYY-MM-DD (BS)") — converted from BS to AD via `NepaliDate`/`bsToAD()` helper before submission.
  - Button "Cancel" — closes modal (does not reset price form fields on cancel, only on successful save).
  - Button "Save"/"Saving…" (disabled while saving).

**Data source:**
- `getProducts()` (via `useApi`) — table rows and Product-select options. Fields: `id`, `name`, `barcode`, `uom`, `tax_class`.
- `getPrices({ active: true })` — used to build `priceMap` (retail) and `wholePriceMap` (wholesale) keyed by `product` id, using fields `tier`, `product`, `price_paisa`.
- `createProduct(data)` / `updateProduct(id, data)` — product modal submit.
- `createPrice(data)` — price modal submit; sends `{ product, tier, price_paisa, valid_from }`.

**Role/access notes:** None visible in this file — no role checks or scoping logic present.

---

## Inventory (`Inventory.jsx`)

**Purpose:** View the stock-movement ledger (production, sales, transfers, returns, wastage, adjustments) across locations and products.

**Layout/structure:** Filter bar (2 selects) above a single scrollable movements table with a footer row summarizing row count.

**Elements:**
- `ErrorBanner` for movement-fetch errors with retry.
- Filter: "Location" select — options "All Locations" + all fetched locations by name. **Disabled** (and pre-set) when the logged-in user's role is `outlet_manager`.
- Filter: "Type" select — options "All" + `production`, `transfer`, `sale`, `return`, `wastage`, `adjustment`.
- Movements table, columns: Date, Type, Product, Location, Qty (kg), Qty (pcs), Lot, Ref.
  - Date → `formatDateString(new Date(m.created_at))`.
  - Type badge, pill-styled, capitalized, color keyed by `TYPE_COLORS` map:
    - `production` → green
    - `sale` → orange
    - `transfer` → blue
    - `return` → purple
    - `wastage` → red
    - `adjustment` (and any unrecognized type, as fallback) → gray
  - Product → `productMap[m.product]?.name`, else raw `m.product`.
  - Location → `locationMap[m.location]?.name`, else raw `m.location`.
  - Qty (kg) → mono, colored green if positive, red if negative, gray if zero/absent; positive values prefixed with `+`; formatted to 3 decimals.
  - Qty (pcs) → same color logic, integer, `+` prefix if positive.
  - Lot → `m.lot` (mono) or "—".
  - Ref → `#{m.ref_id}` or "—".
  - Loading state: 6 skeleton rows (`Skeleton` component, 8 pulsing cells — note: table only has 8 columns so this matches).
  - Empty state: "No movements recorded." spanning all 8 columns.
- Footer: "Showing {movements.length} movement(s)".

**Data source:**
- `getMovements(params)` where `params` conditionally includes `location` and `type` from the two filters. Fields: `id`, `created_at`, `type`, `product`, `location`, `qty_kg`, `qty_pieces`, `lot`, `ref_id`.
- `getLocations()` — builds `locationMap` for name lookups and populates the Location filter's options.
- `getProducts()` — builds `productMap` for name lookups.

**Role/access notes:** For users with `role === 'outlet_manager'`, the Location filter defaults to (and is locked to) `user.assigned_locations[0]` — the select is rendered `disabled`, preventing the outlet manager from viewing other locations' movements client-side.

---

## Transfers (`Transfers.jsx`)

**Purpose:** Record and track stock transfers dispatched between locations, including confirming receipt.

**Layout/structure:** Single action button above a transfers table; one "New Transfer" modal.

**Elements:**
- Button "+ Transfer" — opens the New Transfer modal.
- `ErrorBanner` for load errors with retry.
- Transfers table, columns: Date, From, To, Status, Action.
  - Date → `formatDateString(new Date(t.dispatched_at))`.
  - From/To → resolved via `locationMap`, else raw id.
  - Status badge: `dispatched` → amber pill "Dispatched"; anything else (i.e. received) → green pill "Received".
  - Action: if `status === 'dispatched'`, a "Mark Received" text-link button (shows "Confirming…" and is disabled while that specific row's confirm request, tracked by `confirmingId`, is in flight); otherwise shows "—".
  - Loading state: 4 `Skeleton` rows, 5 pulsing cells each.
  - Empty state: "No transfers yet." spanning 5 columns.
- **New Transfer modal**:
  - Inline error text.
  - Select: "From location" (required) — all locations.
  - Select: "To location" (required) — all locations **except** the currently selected "from" location (filtered by `l.id !== parseInt(form.from_location)`).
  - Button "Cancel".
  - Button "Dispatch"/"Dispatching…" (disabled while saving) — calls `createTransfer` with `dispatched_at: new Date().toISOString()` appended.

**Data source:**
- `getTransfers()` — table rows. Fields: `id`, `dispatched_at`, `from_location`, `to_location`, `status`.
- `getLocations()` — resolves location names and populates both selects.
- `createTransfer(data)` — modal submit.
- `confirmTransferReceipt(id)` — "Mark Received" action; shows toast success ("Transfer received") or error ("Could not confirm receipt — try again") via `useToast`.

**Role/access notes:** None visible — no role-based filtering or gating in this file.

---

## Lots (`Lots.jsx`)

**Purpose:** Record newly received poultry lots (live birds) and view their lifecycle status.

**Layout/structure:** Single action button above a lots table; one "Receive New Lot" modal.

**Elements:**
- Button "+ Receive Lot" — opens the modal.
- `ErrorBanner` for load errors with retry.
- Lots table, columns: Lot Code, Supplier, Live Weight (kg), Bird Count, Received, Status.
  - Lot Code → `lot.code`, mono, brand-primary colored, bold.
  - Supplier → `supplierMap[lot.supplier]?.name` or "—".
  - Live Weight (kg) → mono, `parseFloat(...).toFixed(3)`.
  - Bird Count → mono, `lot.bird_count` or "—".
  - Received → `formatDateString(new Date(lot.created_at))` or "—".
  - Status badge, pill-styled, one of 7 possible lifecycle stages each with distinct coloring:
    - `arrival` → green
    - `grading` → amber
    - `slaughter` → amber (same styling as grading)
    - `storage` → indigo
    - `packaging` → indigo (same styling as storage)
    - `sale` → gray
    - `settlement` → gray (same styling as sale)
  - Loading state: 4 skeleton rows, 6 pulsing cells each.
  - Empty state: "No lots received yet." spanning 6 columns.
- **Receive New Lot modal**:
  - Inline error text.
  - Input: Lot Code (required text, placeholder "e.g. LOT-2083-001", uppercase styling, mono).
  - Select: Source — options "External" (`external`), "Own Farm" (`own`).
  - Select: Supplier (optional) — "None / Own Farm" + all suppliers.
  - Select: Arrival Location (required) — "Select Location…" + all locations.
  - Input: Live Weight (kg) (required number, min 1, step 0.1, mono).
  - Input: Bird Count (required number, min 1, mono).
  - Button "Cancel".
  - Button "Save Lot"/"Saving…" (disabled while saving) — calls `createLot` with `supplier: form.supplier || null` and `bird_count: parseInt(...)`.

**Data source:**
- `getLots()` — table rows. Fields: `id`, `code`, `supplier`, `live_weight_kg`, `bird_count`, `created_at`, `status`.
- `getSuppliers()` — builds `supplierMap` and populates Supplier select.
- `getLocations()` — populates Arrival Location select.
- `createLot(data)` — modal submit.

**Role/access notes:** None visible in this file.

---

## Processing (`Processing.jsx`)

**Purpose:** Read-only log of processing runs (converting live birds to dressed/packaged product), showing yield efficiency.

**Layout/structure:** Single table, no action buttons, no modals, no filters.

**Elements:**
- `ErrorBanner` for load errors with retry.
- Processing runs table, columns: Date, Lot, Live Wt (kg), Dressed Wt (kg), Wastage (kg), Yield %, Processed By.
  - Date → `formatDateString(new Date(row.created_at))` or "—".
  - Lot → `row.lot`, mono, brand-primary color.
  - Live Wt (kg) → `parseFloat(row.input_weight_kg || 0).toFixed(3)`, mono.
  - Dressed Wt (kg) → `parseFloat(row.output_weight_kg || 0).toFixed(3)`, mono.
  - Wastage (kg) → computed client-side as `liveWt - dressedWt`, mono, danger-red color (always styled red regardless of sign).
  - Yield % → computed client-side as `(dressedWt / liveWt) * 100` to 1 decimal, or "—" if `liveWt` is 0; bold mono.
  - Processed By → `row.operator` or "—".
  - Loading state: 4 `Skeleton` rows, 7 pulsing cells each.
  - Empty state: "No processing runs yet." spanning 7 columns.
- No create/edit functionality on this page at all — purely a report view.

**Data source:**
- `getProcessingRuns()` — sole data source. Fields used: `id`, `created_at`, `lot`, `input_weight_kg`, `output_weight_kg`, `operator`.

**Role/access notes:** None visible in this file.

---

## Procurement (`Procurement.jsx`)

**Purpose:** Create and track purchase orders placed with suppliers.

**Layout/structure:** Single action button above a purchase-orders table; one "Create Purchase Order" modal.

**Elements:**
- Button "+ Purchase Order" — opens the modal.
- `ErrorBanner` for load errors with retry.
- Purchase orders table, columns: PO Number, Date, Supplier, Notes, Total (Rs), Status.
  - PO Number → synthesized client-side as `PO-{po.id}` (not a distinct backend field), mono.
  - Date → `formatDateString(new Date(po.created_at))` or "—".
  - Supplier → `supplierMap[po.supplier]?.name` or raw `po.supplier`, bold.
  - Notes → `po.notes` truncated (`max-w-[200px]`) or "—".
  - Total (Rs) → `formatMoney(po.total_paisa)` right-aligned, or "—" if falsy.
  - Status badge, 4 possible states:
    - `draft` → gray
    - `sent` → amber
    - `received` → green
    - `cancelled` → red
  - Loading state: 3 skeleton rows, 7 pulsing cells each (note: table has 6 columns, so the skeleton renders one extra cell than the real table has columns).
  - Empty state: "No purchase orders yet." spanning 6 columns.
- **Create Purchase Order modal**:
  - Inline error text.
  - Select: Supplier (required) — "Select Supplier…" + all suppliers.
  - Input: Notes (optional text).
  - Input: Total (Rs) (required number, min 0, step 0.01) — converted to paisa on submit (`Math.round(parseFloat(...) * 100)`).
  - Button "Cancel".
  - Button "Create PO"/"Creating…" (disabled while saving).

**Data source:**
- `getPurchaseOrders()` — table rows. Fields: `id`, `created_at`, `supplier`, `notes`, `total_paisa`, `status`.
- `getSuppliers()` — builds `supplierMap` and populates Supplier select.
- `createPurchaseOrder(data)` — modal submit, sends `{ supplier, notes, total_paisa }`.

**Role/access notes:** None visible in this file.

---

## Customers (`Customers.jsx`)

**Purpose:** Manage the customer master list (retail/wholesale accounts), including credit limits.

**Layout/structure:** Single action button above a customers table; two modals — "Add Customer" (create) and a "View"/edit modal (opened per-row, doubles as an edit form including credit limit).

**Elements:**
- Button "+ Customer" (`Plus` icon) — opens Add Customer modal.
- `ErrorBanner` for load errors with retry.
- Customers table, columns: Name, Type, PAN, Credit Limit, Action.
  - Name → `c.name`, bold.
  - Type badge: `wholesale` → indigo pill "Wholesale"; anything else → gray pill "Retail".
  - PAN → `c.pan` (mono, small) or "—".
  - Credit Limit → `formatMoney(c.credit_limit_paisa)` if truthy, else "—".
  - Action → "View" text-link button — opens the view/edit modal pre-populated for that customer.
  - Loading state: 4 skeleton rows, 5 pulsing cells each.
  - Empty state: "No customers yet." spanning 5 columns.
- **Add Customer modal**:
  - Inline error text.
  - Input: Name (required text).
  - Select: Type — Retail (`retail`), Wholesale (`wholesale`).
  - Input: PAN Number (optional text, mono).
  - Button "Cancel".
  - Button "Save"/"Saving…" (disabled while saving) — calls `createCustomer` with `pan: form.pan || null`.
- **View/Edit Customer modal** (title = customer's name):
  - Inline error text.
  - Input: Name (required).
  - Select: Type — Retail/Wholesale.
  - Input: PAN Number (optional, mono).
  - Input: Credit Limit (Rs) (number, min 0, step 0.01) — displayed as `credit_limit_paisa / 100`, converted back to paisa on change.
  - Button "Cancel" — closes without saving.
  - Button "Save Changes"/"Saving…" (disabled while saving) — calls `updateCustomer(id, {...})`.

**Data source:**
- `getCustomers()` — table rows and modal seed data. Fields: `id`, `name`, `type`, `pan`, `credit_limit_paisa`.
- `createCustomer(data)` — Add modal submit.
- `updateCustomer(id, data)` — View/Edit modal submit.

**Role/access notes:** None visible in this file.

---

## Invoices (`Invoices.jsx`)

**Purpose:** Browse issued sales invoices with VAT breakdown and CBMS (IRD e-billing) sync status, with print capability.

**Layout/structure:** Single table with paginated footer controls, no create modal (invoices are presumably generated elsewhere, e.g. POS).

**Elements:**
- `ErrorBanner` for load errors with retry.
- Invoices table, columns: Invoice #, Issued, Customer, Taxable (Rs), VAT (Rs), Total (Rs), CBMS, Action.
  - Invoice # → `inv.invoice_number`, mono.
  - Issued → `formatDateString(new Date(inv.issued_at))`.
  - Customer → `inv.customer_name` or "— (walk-in)".
  - Taxable (Rs) → `formatMoney(inv.taxable_paisa)`, right-aligned, mono.
  - VAT (Rs) → `formatMoney(inv.vat_paisa)`, right-aligned, mono.
  - Total (Rs) → `formatMoney(inv.total_paisa)`, right-aligned, mono.
  - CBMS badge, 3 states:
    - `synced` → green pill "Synced"
    - `pending` → amber pill "Pending"
    - `failed` → red pill "Failed"
  - Action → "Print" text-link button, calls `printInvoice(inv)` (imported from local `./printInvoice` helper).
  - Loading state: 5 `Skeleton` rows, 8 pulsing cells each.
  - Empty state: "No invoices yet." spanning 8 columns.
- Pagination footer: "Page {page}" label; "Prev" button (disabled at page 1); "Next" button (disabled when `invoices.length < 50`, implying page size of 50).

**Data source:**
- `getInvoices({ page, ...outletFilter })` — sole data source. Fields: `id`, `invoice_number`, `issued_at`, `customer_name`, `taxable_paisa`, `vat_paisa`, `total_paisa`, `cbms_status`.

**Role/access notes:** If `user.role === 'outlet_manager'` and the user has at least one assigned location, an `outletFilter` object `{ order__fulfilled_location: user.assigned_locations[0] }` is merged into the query params — scoping the invoice list to that outlet manager's first assigned location. Other roles see unfiltered invoices (subject to backend-side scoping).

---

## Sales Reports (`SalesReports.jsx`)

**Purpose:** Tabular sales/orders report with a running page-total for gross revenue.

**Layout/structure:** Single table with a summary total row and paginated footer controls; no filters beyond implicit role-based outlet scoping.

**Elements:**
- `ErrorBanner` for load errors with retry.
- Orders table, columns: Order #, Date, Outlet, Items, Total.
  - Order # → `#{o.id}`, mono.
  - Date → `formatDateString(new Date(o.created_at))` or "—".
  - Outlet → `locationMap[o.fulfilled_location]?.name` or "—".
  - Items → `o.lines?.length` or "—".
  - Total → `formatMoney(o.total_paisa ?? 0)`, right-aligned, bold mono.
  - Loading state: 5 skeleton rows, 5 pulsing cells each.
  - "Page total" summary row (shown whenever `orders.length > 0`) — spans first 4 columns with label "Page total", last cell shows `formatMoney(totalGross)` where `totalGross` is the sum of `total_paisa` across the **currently loaded page** of orders only (not a global total).
  - Empty state: "No sales recorded yet." spanning 5 columns.
- Pagination footer: "Page {page}" label; "Prev" (disabled at page 1); "Next" (disabled when `orders.length < 50`).

**Data source:**
- `getOrders({ page, ...outletFilter })` — table rows and totals. Fields: `id`, `created_at`, `fulfilled_location`, `lines`, `total_paisa`.
- `getLocations()` — builds `locationMap` for outlet name resolution.

**Role/access notes:** Same outlet-scoping pattern as Invoices — if `user.role === 'outlet_manager'` with an assigned location, `outletFilter = { fulfilled_location: user.assigned_locations[0] }` is merged into query params, restricting the report to that outlet.

---

## Users (`Users.jsx`)

**Purpose:** Administer system user accounts — create new users and edit existing users' name, role, and active status.

**Layout/structure:** Page heading + action button row above a users table; two modals — "Add User" (create) and "Edit {username}" (per-row edit).

**Elements:**
- Heading: "User Management".
- Button "+ User" (`Plus` icon) — opens Add User modal.
- `ErrorBanner` for load errors with retry.
- Users table, columns: Username, Full Name, Role, Action.
  - Username → bold.
  - Full Name → `{first_name} {last_name}`.
  - Role badge, capitalized, underscore replaced with space, color per `ROLE_BADGE` map:
    - `superuser` → purple
    - `manager` → blue
    - `outlet_manager` → indigo (lighter variant)
    - `cashier` → indigo (darker variant)
    - `warehouse` → gray
    - any unmapped role → falls back to plain gray (`bg-gray-100 text-gray-600`)
  - Action → "Edit" text-link button — opens the Edit modal pre-populated for that user.
  - Loading state: 4 skeleton rows, 4 pulsing cells each.
  - Empty state: "No users found." spanning 4 columns.
- **Add User modal**:
  - Inline error text (falls back through `err.response.data.detail` → `JSON.stringify(err.response.data)` → generic message).
  - Input: Username (required text).
  - Input: Full Name (optional text) — maps to `first_name`.
  - Select: Role — options Cashier (`cashier`), Manager (`manager`), Outlet Manager (`outlet_manager`), Warehouse Worker (`warehouse`), Procurement (`procurement`), Superuser (`superuser`).
  - Input: Password (required, `type="password"`).
  - Button "Cancel".
  - Button "Save User"/"Saving…" (disabled while saving) — calls `createUser(form)`.
- **Edit User modal** (title "Edit {username}"):
  - Inline error text (same fallback chain).
  - Input: First Name (optional text).
  - Input: Last Name (optional text).
  - Select: Role — same 6 options as Add modal.
  - Checkbox: "Active" — bound to `is_active`.
  - Button "Cancel".
  - Button "Save Changes"/"Saving…" (disabled while saving) — calls `updateUser(id, editForm)`.
  - Note: Edit modal does not include a Username or Password field (only create supports setting username/password).

**Data source:**
- `getUsers()` — table rows. Fields: `id`, `username`, `first_name`, `last_name`, `role`, `is_active`.
- `createUser(data)` — Add User modal submit.
- `updateUser(id, data)` — Edit modal submit.

**Role/access notes:** This page itself has no in-component role gating (any user who can reach the route can use it), but per `AdminLayout.jsx`, the "Users" nav link is `adminOnly`, so only admins (`isAdmin()`) get a nav entry to reach this page. The Role select's `superuser` option lets an admin promote any user to superuser directly from this UI.

---

## Audit Log (`AuditLog.jsx`)

**Purpose:** Read-only system audit trail showing who changed what and when.

**Layout/structure:** Page heading above a single read-only table; no filters, no modals, no actions.

**Elements:**
- Heading: "System Audit Log".
- `ErrorBanner` for load errors with retry.
- Audit log table, columns: Timestamp, User, Action, Model, Details.
  - Timestamp → `formatDateTimeString(log.created_at)` (mono, small) or "—".
  - User → `log.actor`, brand-primary colored, bold.
  - Action → plain bordered badge/chip showing `log.action` verbatim (not color-coded by action type — same neutral styling regardless of value).
  - Model → `log.model_name`, secondary gray text.
  - Details → composite string: `#{object_id}` (or "—" if none) followed by ` — {comma-joined keys of log.diff}` if a diff exists; truncated (`max-w-[300px]`); full diff JSON available via the `title` tooltip attribute (`title={JSON.stringify(log.diff)}`).
  - Loading state: 5 `Skeleton` rows, 5 pulsing cells each.
  - Empty state: "No audit events recorded." spanning 5 columns.

**Data source:**
- `getAuditLogs()` — sole data source. Fields: `id`, `created_at`, `actor`, `action`, `model_name`, `object_id`, `diff`.

**Role/access notes:** No in-component role logic, but per `AdminLayout.jsx` the "Audit Log" nav entry is `adminOnly`, so only admin users (`isAdmin()`) get a nav link to reach this page.

---

## Settings (`Settings.jsx`)

**Purpose:** Preview/placeholder screen for future system configuration (company info, VAT rate, CBMS/IRD integration settings) — explicitly not yet functional.

**Layout/structure:** Page heading + a prominent warning banner, followed by three stacked read-only card sections: "General Configuration", "Financial Configuration", "CBMS Integration (IRD)". No table, no data fetching, no modals.

**Elements:**
- Heading: "System Settings".
- Warning banner (amber): "Read-only preview — the settings backend arrives in Phase 2. Values shown are the current system defaults."
- **General Configuration** card:
  - Input: Company Name — `disabled`, default value "Everfresh Poultry".
  - Input: PAN/VAT Number — `disabled`, mono, default value "123456789".
  - Select: Default Date System — `disabled`, options "Bikram Sambat (BS)" / "Gregorian (AD)" (no bound value/onChange — purely decorative).
- **Financial Configuration** card:
  - Input: Standard VAT Rate (%) — `disabled`, number, default "13".
  - Input: Currency Symbol — `disabled`, text, default "Rs".
- **CBMS Integration (IRD)** card:
  - Checkbox: "Enable real-time CBMS syncing" — `disabled`, defaultChecked true; helper text: "Invoices will be automatically transmitted to IRD upon generation."
  - Input: API Base URL — `disabled`, mono, default "https://cbms.ird.gov.np/api".
  - Input pair: "API Credentials (Username / Password)" — two `disabled` inputs side by side: username (text, default "everfresh_api") and password (`type="password"`, default masked "********").
- No loading, empty, or error states — the entire page is static markup with no API calls.

**Data source:** None. All values are hardcoded `defaultValue`/`defaultChecked` props; no calls into `frontend/src/api/index.js`.

**Role/access notes:** No in-component role logic, but per `AdminLayout.jsx` the "Settings" nav entry is `adminOnly`, so only admin users (`isAdmin()`) get a nav link to reach this page. All form fields are `disabled`, so even admins cannot currently submit changes — consistent with the banner stating the settings backend is a Phase 2 deliverable.
