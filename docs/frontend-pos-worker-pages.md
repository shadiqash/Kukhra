# Everfresh Frontend — POS & Worker Portal UI Inventory

Scope: `App.jsx` routing/shell, `auth/LoginPage.jsx`, the POS module (`PosScreen`, `Cart`, `PaymentModal`, `ShiftModal`, `printReceipt`, offline queue), and the Worker portal (`WorkerLayout` plus its five screens). Read from source on 2026-07-07.

---

## App shell / routing (`App.jsx`)

### Purpose
Top-level router that resolves the signed-in user's role to a landing route and gates each branch (`/pos`, `/admin`, `/worker`) behind role checks.

### Layout/structure
No visual chrome of its own — it is a `<Routes>` tree. Three route subtrees each mount their own layout shell: `PosScreen` (self-contained), `AdminLayout` (nested admin routes, out of scope here), `WorkerLayout` (nested worker routes).

### Elements
- `RoleRoot` — invisible redirect component evaluated at `/`:
  - no user → redirect to `/login`
  - `isCashier()` → redirect to `/pos`
  - `isWorker()` → redirect to `/worker/lot-arrival`
  - `isManager()` or `isAdmin()` → redirect to `/admin`
  - fallback → redirect to `/pos`
- `RequireAuth` — wrapper that redirects to `/login` if no user, or to `/` if the user's role isn't in the route's `allow` list.
- Route table:
  - `/login` → `LoginPage` (or redirect to `/` if already authenticated)
  - `/` → `RoleRoot`
  - `/pos` → `PosScreen`, allowed roles: `cashier`, `manager`, `outlet_manager`, `superuser`
  - `/admin/*` → `AdminLayout` + children, allowed roles: `manager`, `outlet_manager`, `superuser` (with `/admin/users`, `/admin/audit`, `/admin/settings` further restricted to `superuser` only)
  - `/worker/*` → `WorkerLayout` + children, allowed roles: `warehouse`, `procurement`
    - children: `lot-arrival`, `flock-log`, `processing`, `receive-transfer`, `wastage`
  - `*` (catch-all) → redirect to `/`

### Data source
None directly — reads `useAuth()` context state only (`user`, `isCashier`, `isWorker`, `isManager`, `isAdmin`, `hasRole`).

### Role/access notes
- Cashier/manager/outlet_manager/superuser can reach POS; only warehouse/procurement can reach the Worker portal; only manager/outlet_manager/superuser can reach Admin, with users/audit/settings further locked to superuser.
- Role mismatch does not show an error page — it silently redirects to `/` which then re-routes based on the actual role.

---

## Login (`auth/LoginPage.jsx`)

### Purpose
Username/password sign-in screen for all roles, the sole unauthenticated route.

### Layout/structure
Full-screen split layout: left half (desktop only, `hidden lg:flex`) is a branded hero panel with an SVG chicken silhouette, "Everfresh Poultry" title and "Fresh Every Day" tagline on a brand-primary background. Right half is a centered white card (max-width 400px) containing the sign-in form.

### Elements
- Heading: "Welcome back" + subheading "Sign in to continue"
- Username field: text input, required, autofocus, placeholder "Enter username"
- Password field: input toggles `type="password"`/`type="text"`; eye/eye-off icon button (lucide `Eye`/`EyeOff`) inside the field toggles `showPassword` state; placeholder "••••••••"
- Submit button "Sign In" — full width; while `loading` is true it swaps its label for a white spinning ring (`animate-spin` div) and disables itself
- Error banner: appears only after a failed submit — pill-shaped red banner (`bg-red-50`, `text-brand-danger`) with an `AlertTriangle` icon and text "Invalid credentials. Please try again." (this is a generic message regardless of the actual failure cause, since the catch block discards the real error)
- Footer text: "Everfresh Poultry Pvt. Ltd. · Kathmandu"
- No "forgot password," no remember-me, no registration link — the form is minimal by design.

### Data source
Calls `login(username, password)` from `AuthContext` (which itself would call the auth API, e.g. `/auth/token/` per `api/index.js`'s exported `login`). On failure the component catches and shows a generic error; on success `AuthContext` updates `user` and `App.jsx`'s routing takes over.

### Role/access notes
No role gating — this is the entry point for every role. Redirects to `/` automatically if a `user` already exists (handled in `App.jsx`, not in this file).

---

## POS

### PosScreen (`pos/PosScreen.jsx`)

#### Purpose
The cashier's point-of-sale screen: browse/search products, build a cart, and hand off to the payment flow, with offline support.

#### Layout/structure
Full-height flex column: a brand-primary header bar, then a two-pane body — a flexible left pane (search bar + scrollable product grid) and a fixed 288px (`w-72`) right pane that is either the **Cart** (default) or the **PaymentModal** (shown inline in the same panel, not as an overlay, when `showPayment` is true). Two additional overlay modals can appear above everything: the Held Orders panel and `ShiftModal`.

#### Elements
- **Header** (brand-primary bar):
  - "Everfresh POS" title (flex-1)
  - `OFFLINE` badge — amber pill, shown only when `!navigator.onLine`
  - `"{n} Held"` button — amber pill, shown only when `heldOrders.length > 0`; opens the Held Orders overlay
  - Username display (`user?.username`)
  - Shift toggle button — label "Close Shift" (danger-red styling) when a session is open, "Open Shift" (outlined) when not; opens `ShiftModal`
  - "Sign out" text button → calls `logout()`
- **Product search/grid pane**:
  - Search input — placeholder "Search products or scan barcode…"; filters `products` by name (case-insensitive) or barcode substring match
  - Product grid (2/3/4 columns responsive) — one button per product:
    - product name
    - uom label, plus an amber "+VAT" tag if `tax_class === 'taxable'`
    - price (formatted money) in brand-primary bold, or "No price" in muted gray if no active price row exists for the product
    - each button is `disabled` when there is no open shift (`!hasSession`), dimmed to 40% opacity
    - clicking calls `addToCart(product)`
  - Empty state: "No products found" centered text when the filtered list is empty
- **Cart panel** (right, `w-72`), when payment is not showing:
  - Header row: "Cart" title + (only when `lines.length > 0`) "Hold" button (amber outline) and "Void" button (danger outline)
  - `Cart` component (see below) rendering line items and totals
  - Footer: "Pay — {formatMoney(total)}" button, full width, brand-primary; `disabled` when cart is empty or no session is open
  - Helper text "Open a shift to accept payments" (amber) shown under the Pay button when there's no open session
- **Held Orders overlay** (`showHeld`): dark backdrop, white rounded card, "Held Orders" title, scrollable list of held-order buttons each showing item count, formatted grand total, and held time (`toLocaleTimeString`); clicking one calls `resumeHeld(idx)` (with a confirm dialog if the current cart isn't empty — "Replace current cart?"); "Cancel" button closes the overlay.
- **ShiftModal** — rendered when `showShift` is true (see its own section below).
- **Void confirmation** — `voidOrder()` uses the app's shared `useConfirm()` dialog: title "Void this order?", message "All items will be removed from the cart.", confirm label "Void order", styled as a danger action.

#### Data source
- On mount: `getProducts()` and `getPrices({ active: true, tier: 'retail' })` in parallel; results are cached to IndexedDB via `cacheProducts()` and prices indexed by `product` id into a `prices` map. On failure (e.g., offline), falls back to `getCachedProducts()` from IndexedDB.
- `getCounters()` — loads the cashier's counter/outlet; the first result becomes `counter` (supplies `locationId` and `outletName` to `PaymentModal`).
- An `online` event listener plus an immediate on-mount call runs `syncPending()`, which drains any orders saved to the offline queue (see "offline queue" section) whenever the browser is online.
- Cart mutations (`addToCart`, `removeFromCart`, `updateQty`, `holdOrder`, `voidOrder`, `resumeHeld`) are pure client-side state, no API calls.
- Tax math: `vatFor(lines)` sums `line_total_paisa` for lines where `tax_class === 'taxable'`, applies 13% (floored); `grandTotal` = sum of all line totals + VAT.

#### Role/access notes
Route-gated in `App.jsx` to `cashier`, `manager`, `outlet_manager`, `superuser`. Within the screen there's no further per-role branching; access to ring the till is instead gated behind having an **open shift** (`hasSession`) rather than by role — product tiles and the Pay button are disabled without one.

---

### Cart (`pos/Cart.jsx`)

#### Purpose
Presentational line-item list and tax/total breakdown for the current in-progress sale.

#### Layout/structure
Scrollable list of line rows above a fixed tax-breakdown footer; renders a centered empty-state message when there are no lines.

#### Elements
- Empty state: "Cart is empty" (muted, centered) when `lines.length === 0`
- Per line row:
  - product name (truncated)
  - unit price + uom, with amber "+VAT" tag if taxable
  - quantity `<input type="number" min="0.1" step="0.1">` bound to `line.qty`; changing it calls `onQtyChange(idx, value)`
  - line total (formatted money)
  - "×" remove button (hover turns danger-red) → `onRemove(idx)`
- Tax breakdown footer (each row conditional on being non-zero):
  - "Exempt" subtotal
  - "Taxable" subtotal
  - "VAT (13%)" amount, amber/bold
  - "Grand Total" bold, top-bordered

#### Data source
No API calls — pure props (`lines`, `onRemove`, `onQtyChange`) driven by `PosScreen` state. Tax computed identically to `PosScreen`'s `vatFor`/`grandTotal` (13% flat on taxable lines, floored).

#### Role/access notes
None — inherits POS's access gate.

---

### PaymentModal (`pos/PaymentModal.jsx`)

#### Purpose
Collects payment method/amount for the current cart and drives order creation, payment, and fulfillment (online or queued offline), then offers a receipt print.

#### Layout/structure
Renders as an **inline panel** inside the Cart panel's slot in `PosScreen` — explicitly not an overlay/backdrop (per the code comment). Two states: the payment-entry form, and (after `doneOrder` is set) a "Payment Complete" success view.

#### Elements
**Payment-entry view:**
- Title "Payment"
- Total amount, large brand-primary text
- "incl. VAT {amount}" caption if VAT > 0
- Error text (red) shown on failure — two distinct messages depending on whether an order was already created (see below)
- Offline notice — amber banner: "Offline — order will be queued and synced when connection restores." shown whenever `!navigator.onLine`
- Payment method selector — 2-column grid of 4 toggle buttons: **Cash, Card, Esewa, Khalti** (from `METHODS = ['cash','card','esewa','khalti']`); selected method highlighted brand-primary/filled, others outlined; switching method resets `ref` and `tendered`
- Conditional field:
  - if `method === 'cash'`: "Cash Tendered (Rs)" number input (min = total in rupees, placeholder = total); shows a "Change: {amount}" line once tendered ≥ total
  - else (card/esewa/khalti): "Reference / transaction ID" free-text input
- Footer buttons: "Cancel" (outlined, calls `onCancel`) and "Confirm Payment" / "Processing…" while `loading` (brand-primary, disabled while loading)
- Validation: submit blocked with error "Cash tendered is less than total" if cash method and `tenderedPaisa < total`

**Success view (`doneOrder` set):**
- Green checkmark badge icon
- "Payment Complete" heading
- Total amount, large
- Subtext: "Change: {amount}" if cash with change > 0, otherwise the capitalized method name (e.g. "Cash", "Card")
- "Print Receipt" button → calls `printReceipt(...)`
- "Done" button → calls `onSuccess({ order: doneOrder })`, which in `PosScreen` clears the cart and closes the payment panel

#### Data source — exact "Confirm Payment" sequence
On clicking **Confirm Payment**, `submit()` runs:

1. Cash validation: if `method === 'cash'` and `tenderedPaisa < total`, set error and stop (no API calls).
2. Build the order payload: `{ fulfilled_location: locationId, session: session?.id ?? null, source: 'counter', total_paisa: total }`.
3. **Offline branch**: if `!navigator.onLine` and no order has been created yet (`!progress.current.order`), call `cachePendingOrder({ order, lines, payment: { method, ref, amount_paisa: total } })` (writes to the IndexedDB `pending_orders` store) and immediately call `onSuccess({ offline: true })` — no network calls happen at all. `PosScreen` then shows a toast "Order queued (offline)".
4. **Online branch** (or resuming a partially-completed submit — see retry note):
   a. If no order yet: `createOrder(order)` → `POST /orders/`; result cached in `progress.current.order`.
   b. If lines not yet sent: `createOrderLine(...)` → `POST /order-lines/` for every cart line in parallel (`Promise.all`), each payload `{ order: createdOrder.id, product, price, qty_kg, qty_pieces, line_total_paisa }` (qty split into `qty_kg`/`qty_pieces` depending on the product's `uom`); flag `linesDone = true`.
   c. If payment not yet sent: `createPayment({ order: createdOrder.id, method, amount_paisa: total, ref: ref || null })` → `POST /payments/`; flag `paymentDone = true`.
   d. Always (final step, not gated by a "done" flag): `fulfillOrder(createdOrder.id)` → `POST /orders/{id}/fulfill/`, which transitions the order and writes the sale's StockMovements.
   e. On success, `setDoneOrder(createdOrder)` switches to the success view.
5. **Retry-safety**: a `useRef` `progress` object (`{ order, linesDone, paymentDone }`) persists across a failed `submit()` call within the same component instance, so a retry resumes from the step that failed rather than re-creating the order/lines/payment. Error message differs accordingly: "Could not finish the sale. Retry to resume — nothing will be charged twice." if an order already exists, vs. "Payment failed. Check connection and try again." if it failed before the order was created.
6. "Print Receipt" (success view) calls `printReceipt({ order: doneOrder, lines, method, tenderedPaisa, outletName, ref })` — no API call, pure client-side HTML generation/print.

#### Role/access notes
No independent role gating — inherited from the POS route. Needs an active `session` (shift) id, passed down from `PosScreen`; `locationId`/`outletName` come from the cashier's assigned counter.

---

### ShiftModal (`pos/ShiftModal.jsx`)

#### Purpose
Opens and closes a cashier shift (till session), and displays the end-of-shift Z-Report reconciliation.

#### Layout/structure
Fixed full-screen dark backdrop with a centered white rounded card. Three states: Open-Shift form, Close-Shift form, and Z-Report summary (shown after closing).

#### Elements
**Open Shift form** (shown when no `session` prop):
- Title "Open Shift"
- Error text (red) on failure: "Failed to open shift"
- "Opening Float (Rs)" number input, required, step 0.01, min 0
- "Cancel" button → `onDismiss`
- "Open Shift" / "Opening…" submit button (disabled while loading)

**Close Shift form** (shown when a `session` exists):
- Title "Close Shift"
- Subtitle: "Float opened: {formatMoney(opening_float_paisa)}" plus opened-at timestamp if present
- Error text (red) on failure: "Failed to close shift"
- "Counted Cash (Rs)" number input, required, step 0.01, min 0
- "Cancel" button → `onDismiss`
- "Close Shift" / "Closing…" submit button — styled danger-red (disabled while loading)

**Z-Report view** (after successful close):
- Title "Z-Report" + closed-at timestamp (formatted via `formatDateTimeString`)
- Row: Opening Float
- Row: Total Sales ("{n} orders")
- Row: Sales Amount (bold)
- "By Method" section header, then one row per payment method in `zReport.payment_breakdown` (label mapped via `METHOD_LABELS = { cash: 'Cash', card: 'Card', esewa: 'eSewa', khalti: 'Khalti' }`, falling back to raw method string), each showing amount and count; "No payments" text if the breakdown array is empty
- Row: Counted Cash
- Row: Expected Cash (`opening_float_paisa + cash_sales_paisa`)
- Variance row — color-coded: **brand-primary (green-ish)** if `variance_paisa === 0` ("balanced"), **blue** if `variance_paisa > 0` ("over"), **brand-danger (red)** if `variance_paisa < 0` ("short"); value shown as absolute formatted money with a `+`/nothing sign prefix and the word "over"/"short"/"balanced"
- "Print" button → `window.print()`
- "Done" button → clears the Z-report and calls `onClose()`

#### Data source
- `openSession({ counter: counterId, opening_float_paisa })` → `POST /sessions/`. Client-side null-guard: if the response lacks `opened_at`, it's stamped with `new Date().toISOString()` locally.
- `closeSession(session.id, { closing_counted_paisa })` → `POST /sessions/{id}/close/`
- `getSessionSummary(session.id)` → `GET /sessions/{id}/summary/` — populates the Z-report fields (`opening_float_paisa`, `sales_count`, `sales_total_paisa`, `payment_breakdown`, `closing_counted_paisa`, `cash_sales_paisa`, `variance_paisa`, `closed_at`).

#### Role/access notes
No independent gating beyond the POS route; effectively cashier/manager/outlet_manager/superuser as inherited.

---

### printReceipt (`pos/printReceipt.js`)

#### Purpose
Generates an 80mm-thermal-style HTML receipt in a popup window and triggers the browser print dialog.

#### Layout/structure
Not a React component — a plain function that builds an HTML string and opens it in `window.open('', '_blank', 'width=340,height=600')`. Not rendered in the app tree at all; it's a side-effecting utility invoked from `PaymentModal`'s "Print Receipt" button.

#### Elements (of the generated receipt document)
- Store name "Everfresh Poultry" (constant `STORE_NAME`), centered bold
- Outlet name (falls back to constant `STORE_ADDRESS = 'Kathmandu, Nepal'`) if none passed
- PAN line — hardcoded placeholder `123456789` (constant `STORE_PAN`, flagged in a code comment as "replace with actual PAN")
- Receipt # — order id, zero-padded to 6 digits (falls back to `???` if no order id)
- Date/time — Bikram Sambat date via `formatBSDate(now, 'long')` + local time string
- Line items — each row: `*` marker prefix if `tax_class === 'taxable'` (with a legend line "* = VAT taxable item"), product name truncated to 20 chars, then `qty uom x unitPrice = lineTotal`
- Totals block: Exempt / Taxable / VAT 13% (each only if > 0) then bold "TOTAL"
- Payment row: method label (Cash/Card/eSewa/Khalti) + reference in parens if present; "Tendered" row if cash and tendered amount given; "Change" row if change > 0
- Footer: "Thank you for shopping!" / "Everfresh Fresh Every Day"
- Auto-triggers `win.print()` then `win.close()` after a 300ms timeout (to let the popup finish rendering)

#### Data source
No API calls — purely formats data already passed in from `PaymentModal` (`order`, `lines`, `method`, `tenderedPaisa`, `outletName`, `ref`).

#### Role/access notes
None.

---

### Offline queue (`pos/offline/db.js`)

#### Purpose
IndexedDB-backed (via the `idb` library) local persistence for products cache and orders taken while offline, so sales aren't lost without connectivity.

#### Layout/structure
Not UI — a small data-access module. Database `everfresh-pos`, version 1, with two object stores:
- `pending_orders` — keyPath `localId`, auto-incrementing
- `products_cache` — keyPath `id`

#### Elements / operations
- `cachePendingOrder(order)` — adds a `{ order, lines, payment, savedAt }` record (called from `PaymentModal` when offline)
- `getPendingOrders()` — returns all queued orders (used by `PosScreen`'s sync effect)
- `deletePendingOrder(localId)` — removes a synced order from the queue
- `cacheProducts(products)` — bulk-puts product records (called after a successful product fetch in `PosScreen`)
- `getCachedProducts()` — returns cached products as a fallback when the live product fetch fails

#### Data source / sync behavior
`PosScreen`'s `syncPending()` effect (bound to the browser `online` event and run once on mount) walks every queued order and, for each: `createOrder(p.order)` → `createOrderLine(...)` for each line (parallel) → `createPayment({ order: id, ...p.payment })` → `fulfillOrder(id)` → `deletePendingOrder(p.localId)`. This is the same order→lines→payment→fulfill sequence as the live `PaymentModal` path, just replayed from the cached record. If any step throws, the order is left in the queue (caught and silently skipped) to retry on the next `online` event or app load.

#### Role/access notes
None — purely a client storage mechanism shared by any cashier session on that device/browser.

---

## Worker portal

### WorkerLayout (`worker/WorkerLayout.jsx`)

#### Purpose
Mobile-first (max-width 480px) app shell for the Worker PWA: header, dynamic page title, scrollable content outlet, and bottom tab navigation.

#### Layout/structure
Fixed-height (`100dvh`) column: brand-primary top header (24px chicken logo + "Everfresh" + username + logout icon), a white page-title bar below it (title derived from the active nav item), a scrollable `<main>` hosting the routed child (`<Outlet/>`), and an absolutely-positioned bottom nav bar with 5 tabs.

#### Elements
- Header: chicken-silhouette SVG logo, "Everfresh" wordmark, `{user?.username || 'worker'}` text, `LogOut` icon button (title="Logout") → calls `logout()`
- Page title bar: shows the active nav's label ("Arrival", "Flock", "Process", "Transfers", "Wastage") or "Worker Portal" default, computed by matching `location.pathname` against the `NAV` array
- Bottom navigation — 5 `NavLink` tabs, each with a lucide icon and label:
  - Arrival (`Truck`) → `/worker/lot-arrival`
  - Flock (`Bird`) → `/worker/flock-log`
  - Process (`Scissors`) → `/worker/processing`
  - Transfers (`ArrowRightLeft`) → `/worker/receive-transfer`
  - Wastage (`Trash2`) → `/worker/wastage`
  - Active tab: brand-primary color, bold label, filled icon background pill (`bg-[#f0faf8]`), heavier icon stroke width (2.5 vs 2)

#### Data source
No API calls directly — only `useAuth()` for `user`/`logout()`.

#### Role/access notes
Route-gated (in `App.jsx`) to `warehouse` and `procurement` roles. No further per-tab role distinction inside this component — all five tabs are shown to any worker-role user.

---

### LotArrival (`worker/LotArrival.jsx`)

#### Purpose
Form for recording a newly arrived poultry lot (external vendor or own farm) at a location.

#### Layout/structure
Single card containing a vertical form; `ErrorBanner`s above the card for supplier/location fetch failures (with retry).

#### Elements
- `ErrorBanner` for suppliers fetch error (retry button wired to `refetchSuppliers`)
- `ErrorBanner` for locations fetch error (retry button wired to `refetchLocations`)
- "Date (BS)" — read-only text input pre-filled with `getTodayBS()` (today's Bikram Sambat date), non-editable, styled muted
- "Lot Code" — required text input, placeholder "e.g. LOT-2083-001", uppercase styling
- "Source" — required select, options: **External** (`external`, default) / **Own Farm** (`own`)
- "Vendor/Farm" — select populated from `getSuppliers()`; option 0 is "Loading…" while fetching or "None / Own Farm" once loaded; disabled while loading; not required (optional supplier)
- "Arrival Location" — required select populated from `getLocations()`; option 0 is "Loading…" or "Select Location…"; disabled while loading
- "Bird Count (pcs)" — required number input, min 1
- "Total Weight (kg)" — required number input, min 0.1, step 0.1
- Submit button "Record Arrival" / "Saving..." with a `Save` icon; disabled while submitting
- Success/failure feedback via toast: `toast.success('Lot arrived successfully')` or `toast.error(err?.response?.data?.detail ?? 'Failed to record arrival')`; on success the form resets to defaults

#### Data source
- `getSuppliers()`, `getLocations()` via `useApi` hook (auto-fetch + `loading`/`error`/`refetch`)
- Submit: `createLot({ code, source_type, supplier: supplier||null, arrival_location, bird_count: parseInt(...), live_weight_kg })` → `POST /lots/`

#### Role/access notes
Inherits Worker route gating (warehouse/procurement). No in-page role branching.

---

### ProcessingEntry (`worker/ProcessingEntry.jsx`)

#### Purpose
Records a processing run (live weight in → dressed weight out) against an active lot, with live yield/wastage calculation.

#### Layout/structure
Single card with a form; a highlighted stat block shows calculated yield % and wastage kg beneath the weight inputs.

#### Elements
- `ErrorBanner` for lots fetch error (retry via `refetchLots`)
- "Active Lot" — required select, populated from `getLots({ status: 'active' })`, options show lot `code`; placeholder "Loading…"/"Select Lot..."; disabled while loading
- "Live Weight Used (kg)" — required number input, min 0.1, step 0.001
- "Dressed Weight (kg)" — required number input, min 0.1, step 0.001
- Calculated stat panel (green-tinted `bg-[#f0faf8]` box):
  - "Calculated Yield" — percentage = `(output/input)*100`, one decimal; **color-coded**: brand-success (green) if yield ≥ 70%, brand-danger (red) if below 70%
  - "Wastage" — `max(0, input - output)` kg, 3 decimals, always styled brand-danger (red)
  - Caption "Target: ~70–72%"
- Submit button "Save Processing Record" / "Saving..." with `Save` icon; disabled while loading
- Toast feedback: success "Processing data saved" / error `err?.response?.data?.detail ?? 'Failed to save processing record'`; form resets on success

#### Data source
- `getLots({ status: 'active' })` via `useApi`
- Submit: `createProcessingRun({ lot, input_weight_kg, output_weight_kg })` → `POST /processing-runs/`

#### Role/access notes
Inherits Worker route gating. No in-page role branching.

---

### ReceiveTransfer (`worker/ReceiveTransfer.jsx`)

#### Purpose
Lets a worker confirm receipt of an inbound stock transfer that was dispatched from another location.

#### Layout/structure
Either an empty-state card (no pending transfers) or a form card with a select + a details panel that appears once a transfer is chosen.

#### Elements
- `ErrorBanner`s for transfers-fetch and locations-fetch errors (with retries)
- **Empty state** (shown when not loading and zero transfers): green circular `PackageCheck` icon badge, heading "No Pending Transfers", subtext "You have received all dispatched items."
- **Form state** (when transfers exist):
  - "Select Incoming Transfer" — required select, populated from `getTransfers({ status: 'dispatched' })`; each option labeled `#{id} — from {locationName}` (location name resolved via a `locationMap` built from `getLocations()`, falling back to the raw id if not found)
  - Transfer details panel (shown once a transfer is selected): `AlertCircle` icon, "Transfer Details" heading, "From: {location}" line, "Dispatched: {date}" line (formatted via `formatDateString`, or "—" if no dispatched_at)
  - Submit button "Confirm Receipt" / "Confirming..." with `PackageCheck` icon; disabled while loading or when nothing is selected
  - Toast feedback: success "Transfer received successfully" (clears selection and refetches the transfer list) / error `err?.response?.data?.detail ?? 'Failed to confirm receipt'`

#### Data source
- `getTransfers({ status: 'dispatched' })`, `getLocations()` via `useApi`
- Submit: `confirmTransferReceipt(selectedId)` → `POST /transfers/{id}/confirm-receipt/`

#### Role/access notes
Inherits Worker route gating. No in-page role branching.

---

### Wastage (`worker/Wastage.jsx`)

#### Purpose
Records product wastage (spoilage/loss) at a location, deducting stock via a negative-quantity stock movement.

#### Layout/structure
Single card with a straightforward 3-field form.

#### Elements
- `ErrorBanner`s for products-fetch and locations-fetch errors (with retries)
- "Product" — required select, populated from `getProducts()`; placeholder "Loading…"/"Select Product..."; disabled while loading
- "Location" — required select, populated from `getLocations()`; placeholder "Loading…"/"Select Location..."; disabled while loading
- "Weight (kg)" — required number input, min 0.001, step 0.001
- Submit button "Record Wastage" / "Recording..." with `Trash2` icon; styled distinctly danger-red (`bg-[#b91c1c]`, hover `#991b1b`) rather than the standard brand-primary used elsewhere in the Worker portal; disabled while loading
- Toast feedback: success "Wastage recorded successfully" / error `err?.response?.data?.detail ?? 'Failed to record wastage'`; form resets on success

#### Data source
- `getProducts()`, `getLocations()` via `useApi`
- Submit: `createWastage({ product, location, qty_kg })`. Note the API layer (`api/index.js`) wraps this: it posts to `POST /movements/` with `type: 'wastage'` and force-negates the quantity (`qty_kg: -Math.abs(parseFloat(qty_kg) || 0)`) per the ledger convention that wastage removes stock.

#### Role/access notes
Inherits Worker route gating. No in-page role branching.

---

### FlockLog (`worker/FlockLog.jsx`)

#### Purpose
Placeholder screen intended for daily flock logging (feed, mortality, medication); currently read-only/non-functional.

#### Layout/structure
Two stacked cards: a summary card showing the current active lot, and a large centered placeholder card in the remaining space.

#### Elements
- "Current Active Lot" card: lot `code` (brand-primary, monospace) or "None active" if no active lot; if an active lot exists, a right-aligned "Live Weight" figure (`live_weight_kg`, 1 decimal, defaults to 0 if missing)
- "Today's Log ({BS date})" section header (uses `getTodayBS()`) — label only, no content beneath it
- Placeholder card: dimmed `ClipboardList` icon, text "Flock logging (feed, mortality, medication) is coming in Phase 2.", secondary caption "Until then, record observations in the paper register."
- **No form, no inputs, no submit button, no toasts** — this screen is entirely non-interactive aside from the underlying bottom-nav.

#### Data source
- `getLots({ status: 'active' })` via `useApi`; only the first result (`lots[0]`) is used as `activeLot`. No mutation calls exist in this file at all — it never writes anything.

#### Role/access notes
Inherits Worker route gating. Confirmed as a known Phase 1 gap/placeholder (matches the "Phase 2 gaps documented" note from the prior QA pass) — flock feed/mortality/medication logging is not yet implemented in the frontend.
