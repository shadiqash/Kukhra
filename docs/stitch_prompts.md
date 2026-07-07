# Everfresh Poultry — Google Stitch UI Prompts
# 26 screens across 4 portals

## DESIGN SYSTEM (apply to all screens)
- Primary: #00352e (deep forest green) — headers, primary buttons, active states
- Secondary: #904d00 (warm amber) — accents, badges, warnings
- Surface: #f9faf7 (warm off-white) — page background
- White: #ffffff — card/panel backgrounds
- Border: #e3e8e6 — card borders, dividers
- Text primary: #111a18
- Text secondary: #4a6360
- Danger: #b91c1c — void, delete actions
- Success: #166534 — confirmed, paid states
- UI font: Hanken Grotesk, weights 400/500/600/700
- Number font: JetBrains Mono, weight 400/500 — all prices, quantities, IDs
- Border radius: 12px cards, 8px buttons/inputs, 20px pills
- Shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)

---

## GROUP 1 — SHARED

---

### PROMPT 1 — Login Screen (All Roles)

Design a full-page login screen for "Everfresh Poultry Management System", a Nepal-based chicken retail and distribution platform.

**Device:** Desktop/tablet, 1280×800, responsive.

**Background:** Full viewport covered with a subtle pattern or texture in #f9faf7. Left half (desktop) shows a large hero image area with a deep forest green (#00352e) overlay, the Everfresh logo centered in white (a stylized chicken silhouette + wordmark "Everfresh Poultry" in Hanken Grotesk 700, 28px), and a tagline "Fresh Every Day" in white/60% opacity below it.

**Right half / center (mobile):** White card, 400px wide, border-radius 16px, shadow medium, centered vertically. Contents top to bottom:

1. "Welcome back" — Hanken Grotesk 600, 24px, #111a18
2. "Sign in to continue" — 14px, #4a6360, margin-bottom 32px
3. Label "Username" — 13px, 500, #4a6360
   - Input field: full width, 48px height, border 1.5px #e3e8e6, radius 8px, placeholder "Enter username", font Hanken Grotesk 400, 15px, padding 0 16px
   - Focus state: border #00352e, box-shadow 0 0 0 3px rgba(0,53,46,0.12)
4. Label "Password" — same style
   - Password input with show/hide toggle icon (eye icon, right side, #4a6360)
5. "Sign In" button — full width, 48px height, background #00352e, text white, Hanken Grotesk 600, 15px, radius 8px, hover: #004a3f
   - Loading state: spinner replaces text
6. Error state (inline, below button): red pill badge "Invalid credentials. Please try again." with ⚠ icon, background #fef2f2, text #b91c1c, 13px
7. Footer text: "Everfresh Poultry Pvt. Ltd. · Kathmandu" — 12px, #4a6360, centered

**Sample credentials shown as placeholder hint:** username "admin", password "••••••••"

**No "forgot password" link** — admin resets from Users screen.

---

## GROUP 2 — POS PORTAL (Cashier, Touch-optimized Tablet)

Device for all POS screens: 1024×768 landscape tablet. Touch targets minimum 52px height. No hover-only interactions.

---

### PROMPT 2 — POS Main Screen

Design the main Point-of-Sale screen for a cashier at Everfresh Baneshwor outlet. This is a touch-first tablet POS for selling chicken products. Speed is everything — a cashier should be able to ring up 3 items and take payment in under 10 seconds.

**Device:** 1024×768 landscape tablet, full screen.

**Layout:** Three-zone horizontal split:

---

**ZONE A — Top header bar** (full width, 56px tall, background #00352e)
- Left: "Everfresh POS" in white, Hanken Grotesk 700, 18px
- Center: Outlet badge "Baneshwor" in white/80%, 14px, with location pin icon
- Right side icons (left to right, each 44×44px touch target):
  - Wifi indicator (green dot = online, amber dot = offline)
  - "2 Held" amber pill badge (shown when held orders exist) — Hanken Grotesk 600, 12px, background #904d00, text white, pill shape, 28px height
  - "Ramesh Oli" text in white/80%, 13px
  - "Close Shift" button — border 1.5px #ef4444, text #ef4444, radius 20px, 32px height, 14px, hover: background #ef4444, text white
  - Sign out icon button (door arrow icon), white/60%

---

**ZONE B — Product Grid** (left 60% of screen below header, background #f9faf7, padding 16px)

Top row: Search bar — full width, 48px height, radius 24px, background white, border 1.5px #e3e8e6, search icon left, placeholder "Search or scan barcode…", Hanken Grotesk 400, 15px

Below: scrollable grid, 4 columns, gap 12px. Each product card (white, radius 12px, border 1.5px #e3e8e6, padding 14px, shadow-sm):
- Product name: Hanken Grotesk 600, 14px, #111a18, 2 lines max
- Unit: 12px, #4a6360 (e.g. "kg", "piece")
- VAT badge (if taxable): tiny amber pill "+VAT" — 10px, #904d00 background tint, right-aligned
- Price: JetBrains Mono 600, 18px, #00352e (e.g. "Rs 420")
- Tap anywhere on card to add to cart
- Active/just-tapped state: border #00352e, background #f0faf8, scale 0.97, 80ms transition

Sample products in grid:
Row 1: "Whole Chicken (Fresh)" Rs 420/kg | "Whole Chicken (Dressed)" Rs 450/kg | "Country Chicken (Deshi)" Rs 850/kg | "Chicken Breast (Boneless)" Rs 580/kg
Row 2: "Chicken Leg Quarter" Rs 380/kg | "Chicken Wing" Rs 330/kg | "Chicken Thigh" Rs 400/kg | "Chicken Liver" Rs 250/kg
Row 3: "Chicken Gizzard" Rs 220/kg | "Chicken Feet" Rs 150/kg | "Egg (Tray 30pcs)" Rs 600/pc | "Chicken Sausage 500g" Rs 390/pc +VAT

Disabled state (no shift open): cards 40% opacity, cursor disabled, no tap response.
"No products found" empty state: centered illustration, "No products found" 14px #4a6360.

---

**ZONE C — Cart Panel** (right 40% of screen, background white, border-left 1.5px #e3e8e6, flex column)

**Cart header** (padding 16px 16px 12px, border-bottom 1.5px #e3e8e6):
- "Cart" — Hanken Grotesk 600, 16px, #111a18, left
- Right side (only when cart has items): two text-buttons:
  - "Hold" — 13px, #904d00, border 1px #904d00, radius 6px, 32px height, 10px padding
  - "Void" — 13px, #b91c1c, border 1px #b91c1c, radius 6px, 32px height, 10px padding

**Cart body** (flex-1, overflow-y auto):

Each cart line item (padding 12px 16px, border-bottom 1px #f0f0f0):
- Product name: Hanken Grotesk 500, 14px, #111a18, truncate 1 line
- Sub-row: unit price "Rs 420 / kg" — 12px, #4a6360, JetBrains Mono for price
- If taxable: "+VAT" text in amber 12px after unit
- Right side: quantity input (white, border 1.5px #e3e8e6, radius 6px, 40×40px, center-aligned, JetBrains Mono, text 16px) with – and + buttons (32×40px each, adjacent)
- Line total: JetBrains Mono 600, 15px, #111a18, right-aligned
- × remove button: 24×24px, #4a6360, top-right of row

Sample cart (3 items):
- Whole Chicken (Fresh) | Rs 420 / kg | qty: 2.500 | Rs 1,050
- Chicken Breast (Boneless) | Rs 580 / kg | qty: 1.000 | Rs 580
- Chicken Sausage 500g +VAT | Rs 390 / pc | qty: 2 | Rs 780

**Cart footer** (padding 16px, border-top 1.5px #e3e8e6, background #fafafa):

Tax breakdown section (shown only when cart has items, 13px, spacing 6px between rows):
- "Exempt" row: label left, "Rs 1,630.00" JetBrains Mono right, color #4a6360
- "Taxable" row: label left, "Rs 780.00" right, color #4a6360
- "VAT (13%)" row: label left, "Rs 101.00" right, color #904d00, font-weight 600
- Divider 1px #e3e8e6
- "Grand Total" row: Hanken Grotesk 700, 18px, #111a18, JetBrains Mono 700 for amount "Rs 2,511.00"

**"Pay" button** (full width, 56px height, background #00352e, text white, Hanken Grotesk 700, 17px, radius 10px):
Label: "Pay  ·  Rs 2,511.00" (middle dot separator)
Disabled state (no session or empty cart): opacity 40%, background #00352e

"Open a shift to accept payments" — 12px, #904d00, centered, shown when no session

**Empty cart state** (zone C body, centered): shopping bag outline icon in #e3e8e6, 48px, "Cart is empty" 14px #4a6360 below

---

### PROMPT 3 — Payment Modal

Design a modal overlay for the Everfresh POS payment flow. Appears centered over the POS main screen with a dark backdrop (rgba 0,0,0,0.45). Modal is white, 400px wide, radius 20px, shadow-xl, padding 28px.

**Modal contents top to bottom:**

**Header:** "Payment" — Hanken Grotesk 700, 20px, #111a18

**Amount display** (centered, margin 16px 0 20px):
- "Rs 2,511.00" — JetBrains Mono 700, 38px, #00352e
- Sub-line: "incl. VAT Rs 101.00" — 13px, #904d00, shown only when VAT > 0

**Offline warning banner** (amber, shown when offline only):
Background #fef3c7, border 1px #f59e0b, radius 8px, padding 10px 14px
"⚠ Offline — order will be queued and synced when online" — 13px, #92400e

**Payment method selector** — 2×2 grid of method buttons, gap 10px:
Each button: 96px tall, radius 10px, border 1.5px #e3e8e6, flex column center:
- Icon (32px): cash bills / credit card / eSewa logo / Khalti logo
- Label: Hanken Grotesk 600, 14px
Methods: Cash | Card | eSewa | Khalti
Selected state: background #f0faf8, border 2px #00352e, label color #00352e

**Cash tendered field** (shown only when Cash selected):
Label: "Cash Tendered (Rs)" — 13px, #4a6360
Input: 48px height, radius 8px, border 1.5px #e3e8e6, JetBrains Mono 400, 18px, placeholder "2,511.00"
Focus: border #00352e
Change row (shown when tendered > total): "Change: Rs 489.00" — JetBrains Mono 600, 16px, #166534, background #f0fdf4, radius 6px, padding 8px 12px, margin-top 8px

**Reference input** (shown for Card/eSewa/Khalti):
Placeholder "Reference / transaction ID", 44px height, 14px

**Action buttons** (side by side, gap 12px, margin-top 20px):
- "Cancel" — flex 1, border 1.5px #e3e8e6, text #4a6360, 48px height, radius 10px
- "Confirm Payment" — flex 1, background #00352e, text white, 48px height, radius 10px, Hanken Grotesk 700
  - Loading state: spinner + "Processing…"

Error state: red inline banner below buttons "Payment failed. Check connection and try again."

---

### PROMPT 4 — Payment Success / Receipt Screen

Design the payment success state inside the Everfresh POS payment modal. Same modal container as the payment screen (400px wide, white, radius 20px, padding 28px) but replaced with a success view.

**Contents top to bottom:**

**Success icon:** Circle 64px, background #dcfce7, centered. Inside: checkmark icon 32px, color #166534. Subtle pulse animation on appear.

**"Payment Complete"** — Hanken Grotesk 700, 22px, #111a18, centered, margin-top 16px

**Amount:** "Rs 2,511.00" — JetBrains Mono 700, 32px, #00352e, centered

**Payment info row** (centered, 14px, #4a6360, margin-top 8px):
Cash payment: "Change: Rs 489.00" in #166534, Hanken Grotesk 600
Non-cash: method name only e.g. "eSewa · REF-20834"

**Divider** (1px #e3e8e6, margin 20px 0)

**Receipt preview snippet** (background #f9faf7, radius 10px, padding 14px, JetBrains Mono 12px, #4a6360, 5 lines visible):
```
EVERFRESH POULTRY
Baneshwor, Kathmandu
Receipt #000042 · 09 Ashadh 2083
——————————————————
Whole Chicken    2.5kg  Rs 1,050
Chicken Breast   1.0kg  Rs   580
Sausage 500g*    2pcs   Rs   780
——————————————————
VAT(13%): Rs 101  Total: Rs 2,511
```

**Action buttons** (side by side, gap 12px):
- "Print Receipt" — flex 1, border 1.5px #00352e, text #00352e, 48px, radius 10px, printer icon left
- "Done" — flex 1, background #00352e, text white, 48px, radius 10px, Hanken Grotesk 700

---

### PROMPT 5 — Open Shift Modal

Design the "Open Shift" modal for Everfresh POS. White modal, 380px wide, radius 20px, shadow-xl, centered over the POS screen with backdrop.

**Contents:**

**Header:** "Open Shift" — Hanken Grotesk 700, 20px, #111a18
**Subheader:** "Baneshwor Counter · Ramesh Oli" — 14px, #4a6360, margin-bottom 24px

**Opening Float field:**
Label: "Opening Float (Rs)" — 13px, 500, #4a6360
Input: 52px height, radius 8px, border 1.5px #e3e8e6, JetBrains Mono 400, 20px, placeholder "0.00", left-aligned Rs prefix in #4a6360

Info note: "Enter the cash count in the till before first sale" — 12px, #4a6360, italic, margin-top 6px

**Error state:** "Failed to open shift — check your connection." red inline 13px

**Action buttons** (side by side, margin-top 24px):
- "Cancel" — border 1.5px #e3e8e6, text #4a6360, flex 1, 48px
- "Open Shift" — background #00352e, text white, flex 1, 48px, Hanken Grotesk 700
  Loading: "Opening…" with spinner

---

### PROMPT 6 — Close Shift + Z-Report Modal

Design a two-state modal for closing a cashier shift and displaying the Z-report. White modal, 420px wide, radius 20px, shadow-xl.

**STATE 1: Close Shift form** (padding 28px):

"Close Shift" — Hanken Grotesk 700, 20px
"Float opened: Rs 500.00 · 09 Ashadh 2083, 09:15 AM" — 13px, #4a6360, margin-bottom 20px

**Counted Cash field:**
Label: "Counted Cash (Rs)" — 13px, 500
Input: 52px, JetBrains Mono 20px, placeholder "0.00"

Buttons: "Cancel" + "Close Shift" (background #b91c1c, white text, 48px)

---

**STATE 2: Z-Report** (shown after close succeeds, same modal, padding 28px):

Header row:
- "Z-Report" — Hanken Grotesk 700, 20px, left
- "09 Ashadh 2083, 06:43 PM" — 12px, #4a6360, right

Divider. Then data rows in a clean two-column list (label left, value right), 36px row height, alternating background #fafafa / white, border-bottom 1px #f0f0f0, padding 0 0:

- Opening Float | Rs 500.00 (JetBrains Mono)
- [divider with label "Sales"]
- Total Orders | 12
- Sales Amount | **Rs 18,420.00** (bold)
- [divider with label "By Payment Method"]
- Cash | Rs 12,000.00 (4 orders)
- Card | Rs 3,800.00 (2 orders)
- eSewa | Rs 2,620.00 (6 orders)
- [divider with label "Cash Reconciliation"]
- Cash Sales | Rs 12,000.00
- Opening Float | Rs 500.00
- Expected Cash | Rs 12,500.00
- Counted Cash | Rs 12,500.00
- Variance | **Rs 0.00 — Balanced** (text #166534, bold)

(Shortage example: "Rs 200.00 short" in #b91c1c; Overage: "Rs 150.00 over" in #1d4ed8)

Action buttons (margin-top 20px):
- "Print" — border 1.5px #00352e, text #00352e, flex 1, 48px, printer icon
- "Done" — background #00352e, text white, flex 1, 48px

---

### PROMPT 7 — Held Orders Panel

Design a slide-up modal panel for managing held orders in Everfresh POS. Appears from bottom of screen, height auto (max 60vh), radius 16px top corners, white background, dark backdrop.

**Header bar** (padding 16px 20px, border-bottom 1.5px #e3e8e6):
- "Held Orders" — Hanken Grotesk 700, 18px, #111a18
- Count pill: "2 held" — amber pill, #904d00 bg, white text, 12px, right
- × close button, top right, 36×36px

**List of held orders** (scrollable, max 4 visible):

Each card (white, margin 12px 16px, border 1.5px #e3e8e6, radius 12px, padding 14px 16px, flex row):
- Left: Stack of product names truncated "Whole Chicken, Breast, Sausage…" — 14px, #111a18
  Below: "3 items" — 12px, #4a6360
- Right: Amount "Rs 2,511.00" — JetBrains Mono 600, 16px, #00352e
  Below: time held "Held 4 mins ago" — 12px, #4a6360
- Full card is tappable (tap to resume), hover: border #00352e

**Empty state:** "No held orders" centered, 14px, #4a6360

**Footer** (padding 16px):
- "Cancel" button full width, border 1.5px #e3e8e6, text #4a6360, 48px

Confirmation overlay when resuming with existing cart: "Replace your current cart?" — small dialog, "Keep Current" (outline) + "Resume Held" (#00352e solid)

---

## GROUP 3 — ADMIN PORTAL (Manager/Superuser, Desktop)

Device for all Admin screens: 1440×900 desktop. Layout: left sidebar navigation + main content area. Sidebar is always visible.

**Sidebar spec (shared across all Admin screens):**
- Width 240px, background #00352e, full height
- Top: Everfresh logo (white wordmark + chicken icon), 24px, padding 24px 20px, border-bottom 1px rgba(255,255,255,0.1)
- Nav items (padding 10px 16px, radius 8px, margin 2px 8px, Hanken Grotesk 500, 14px, color white/70%):
  - Dashboard (grid icon)
  - Products (package icon)
  - Inventory (layers icon)
  - Transfers (arrow-right-left icon)
  - Invoices (receipt icon)
  - Sales Reports (bar-chart icon)
  - Lots (box icon)
  - Processing (scissors icon)
  - Procurement (truck icon)
  - Customers (users icon)
  - Users (user-cog icon)
  - Audit Log (clock icon)
  - Settings (gear icon)
  - Active item: background rgba(255,255,255,0.12), color white, font-weight 600
- Bottom: user info "Admin · admin" white/70%, 13px, with sign-out icon

**Top bar (shared, right of sidebar):** height 56px, background white, border-bottom 1.5px #e3e8e6, padding 0 24px. Left: current page title Hanken Grotesk 700, 18px. Right: today's BS date "09 Ashadh 2083" 13px #4a6360, JetBrains Mono for date numbers.

---

### PROMPT 8 — Admin Dashboard

Design the admin dashboard screen for Everfresh Poultry. Sidebar + top bar as described. Main content area background #f9faf7, padding 24px.

**KPI Cards row** (4 cards, equal width, gap 16px, margin-bottom 24px):

Each card: white, radius 12px, border 1.5px #e3e8e6, padding 20px 24px, shadow-sm:

1. **Today's Revenue**
   Label: "Today's Revenue" — 12px, #4a6360, uppercase tracking-wide
   Value: "Rs 84,250.00" — JetBrains Mono 700, 28px, #111a18
   Sub: "↑ 12% vs yesterday" — 13px, #166534
   Icon right: coin stack in #f0faf8 circle 40px

2. **Orders Today**
   Value: "34"
   Sub: "↑ 5 vs yesterday"
   Icon: shopping bag

3. **Active Outlets**
   Value: "11 / 12"
   Sub: "Jawalakhel offline"
   Icon: map-pin
   Sub color: #904d00

4. **Low Stock Alerts**
   Value: "3"
   Sub: "Requires attention"
   Icon: alert-triangle
   Value color: #b91c1c

**Two-column layout below (left 65%, right 35%, gap 16px):**

LEFT: "Recent Orders" card (white, radius 12px, border 1.5px #e3e8e6, padding 0, overflow hidden):
- Card header: "Recent Orders" Hanken Grotesk 600 16px, padding 16px 20px, border-bottom, + "View All →" link 13px #00352e right
- Table (full width, 13px):
  - Columns: Order # | Date | Outlet | Items | Total | Status
  - Header row: background #f9faf7, text 11px uppercase #4a6360, padding 10px 16px
  - Data rows (5 rows, padding 12px 16px, border-bottom 1px #f0f0f0, hover #fafafa):
    - #000041 | 09 Ashadh 2083 | Baneshwor | 3 | Rs 2,511 | ✓ Fulfilled (green pill)
    - #000040 | 09 Ashadh 2083 | Thamel | 1 | Rs 580 | ✓ Fulfilled
    - #000039 | 09 Ashadh 2083 | Koteshwor | 5 | Rs 4,200 | ✓ Fulfilled
    - #000038 | 09 Ashadh 2083 | Lazimpat | 2 | Rs 1,630 | ✓ Fulfilled
    - #000037 | 09 Ashadh 2083 | Chabahil | 4 | Rs 3,120 | ✓ Fulfilled
  - JetBrains Mono for order #, total

RIGHT: "Stock Alerts" card (white, radius 12px, border 1.5px #e3e8e6, padding 0):
- Header: "Low Stock Alerts" 16px 600, padding 16px 20px, border-bottom
- 3 alert rows (padding 14px 20px, border-bottom 1px #f0f0f0):
  Each row: ⚠ amber icon | Product name 14px | "Thamel" outlet 12px gray | "0.8 kg remaining" amber bold right
  - ⚠ Chicken Liver · Thamel · 0.8 kg
  - ⚠ Chicken Feet · Koteshwor · 1.2 kg
  - ⚠ Chicken Gizzard · Baneshwor · 0.5 kg

Below right: "Today's Sales by Outlet" card:
Simple list (outlet name left, bar right that fills proportional to revenue, Rs value right, 13px):
- Baneshwor ████████ Rs 18,420
- Thamel ██████ Rs 14,100
- Lazimpat █████ Rs 11,200
- Koteshwor ████ Rs 9,800
- Kalanki ███ Rs 7,200
(+ 7 more)

---

### PROMPT 9 — Products Management Screen

Design the Products management screen for Everfresh admin portal. Sidebar + top bar as described. Page title "Products". Main area background #f9faf7, padding 24px.

**Action bar** (margin-bottom 20px, flex row, gap 12px):
- "+ Price" button — border 1.5px #00352e, text #00352e, 40px height, radius 8px, 14px, hover: background #f0faf8
- "+ Product" button — background #00352e, text white, 40px, radius 8px, Hanken Grotesk 600, 14px

**Products table card** (white, radius 12px, border 1.5px #e3e8e6, overflow hidden, shadow-sm):

Table header row (background #f9faf7, border-bottom 1.5px #e3e8e6, padding 11px 16px):
Columns: Name | Barcode | UoM | Weighed | Tax | Retail Price | Wholesale Price | Action
All header labels: 11px, uppercase, tracking-widest, #4a6360, Hanken Grotesk 500

Data rows (14px, border-bottom 1px #f0f0f0, padding 13px 16px, hover #fafafa):

Row 1: Whole Chicken (Fresh) | 8901030001 (JetBrains Mono 12px gray) | kg | Yes | Exempt (gray pill) | Rs 420.00 (JetBrains Mono) | Rs 378.00 | Edit button (outline, 12px)
Row 2: Whole Chicken (Dressed) | 8901030002 | kg | Yes | Exempt | Rs 450.00 | Rs 405.00 |
Row 3: Country Chicken (Deshi) | 8901030003 | kg | Yes | Exempt | Rs 850.00 | Rs 765.00 |
Row 4: Chicken Breast (Boneless) | 8901030010 | kg | Yes | Exempt | Rs 580.00 | Rs 522.00 |
Row 5: Chicken Leg Quarter | 8901030011 | kg | Yes | Exempt | Rs 380.00 | Rs 342.00 |
Row 6: Chicken Sausage 500g | 8901030020 | piece | No | **Taxable (amber pill)** | Rs 390.00 | Rs 351.00 |
Row 7: Chicken Momo (Frozen) 300g | 8901030021 | piece | No | Taxable | Rs 280.00 | Rs 252.00 |
Row 8: Marinated Chicken Tikka | 8901030022 | kg | Yes | Taxable | Rs 620.00 | Rs 558.00 |
(…12 more rows)

Tax class styling: "Exempt" — gray pill background #f3f4f6 text #4a6360; "Taxable" — amber pill background #fef3c7 text #92400e

**Add Product modal** (shown on "+ Product" click):
Modal 480px wide, white, radius 20px, shadow-xl, padding 28px:
Title "Add Product" 20px 700
Fields (label + input, gap 16px):
- Name (text input, 44px, radius 8px)
- Barcode (text input, placeholder "Scan or type…")
- Unit of Measure (select: kg / piece)
- Tax Class (select: Exempt / Taxable (13% VAT)) — amber highlight when Taxable selected
Buttons: "Cancel" outline + "Save" #00352e solid, 44px

**Add Price modal** (shown on "+ Price" click):
Fields: Product (select dropdown with all products), Tier (Retail / Wholesale / Member), Price (Rs, number), Valid From (date picker)

---

### PROMPT 10 — Inventory Movements Screen

Design the Inventory Movements screen for Everfresh admin. Shows an append-only log of all stock movements across all outlets. Sidebar + top bar, page title "Inventory Movements".

**Filter bar** (white card, radius 12px, border 1.5px #e3e8e6, padding 16px 20px, margin-bottom 20px, flex row, gap 12px, align-center):
- "Location:" label 13px gray + Select dropdown (All Locations / Baneshwor / Thamel / Koteshwor / Kalanki / Chabahil / Jawalakhel / Lazimpat / Pulchowk / Sanepa / Gongabu / Boudha / Central Warehouse – Balaju / Processing Plant – Balaju) — 180px wide, 40px height
- "Type:" label + Select (All / production / transfer / sale / return / wastage / adjustment) — 160px
- Both selects: Hanken Grotesk 400, 14px, border 1.5px #e3e8e6, radius 8px

**Movements table** (white, radius 12px, border 1.5px #e3e8e6, overflow hidden):

Header: Date | Type | Product | Location | Qty (kg) | Qty (pcs) | Lot | Ref
All: 11px uppercase #4a6360, padding 11px 16px, background #f9faf7

Rows (padding 12px 16px, border-bottom 1px #f0f0f0, 13px):

Row 1: 09 Ashadh 2083 | **sale** (orange pill) | Whole Chicken (Fresh) | Baneshwor | –2.500 (red, JetBrains Mono) | — | — | #41
Row 2: 09 Ashadh 2083 | **production** (green pill) | Whole Chicken (Fresh) | Processing Plant | +85.000 (green, JetBrains Mono) | — | LOT-2083-047 | —
Row 3: 09 Ashadh 2083 | **transfer** (blue pill) | Chicken Breast | Central Warehouse | –20.000 (red) | — | LOT-2083-045 | T#18
Row 4: 09 Ashadh 2083 | **transfer** (blue pill) | Chicken Breast | Thamel | +20.000 (green) | — | LOT-2083-045 | T#18
Row 5: 08 Ashadh 2083 | **sale** (orange) | Chicken Sausage 500g | Koteshwor | — | –4 (red) | — | #38
Row 6: 08 Ashadh 2083 | **wastage** (red pill) | Chicken Liver | Processing Plant | –0.800 | — | LOT-2083-043 | —
Row 7: 08 Ashadh 2083 | **return** (purple pill) | Whole Chicken | Baneshwor | +1.000 (green) | — | — | #35

Type pill colors:
- production: background #dcfce7 text #166534
- sale: background #ffedd5 text #c2410c
- transfer: background #dbeafe text #1d4ed8
- return: background #f3e8ff text #7e22ce
- wastage: background #fee2e2 text #b91c1c
- adjustment: background #f3f4f6 text #374151

Negative quantities: #b91c1c, JetBrains Mono
Positive quantities: #166534, JetBrains Mono

Pagination: "Showing 1–25 of 847 movements" + Prev/Next buttons, 13px, bottom right

---

### PROMPT 11 — Stock Transfers Screen

Design the Stock Transfers screen for Everfresh admin. Shows warehouse-to-outlet transfers. Sidebar + top bar, page title "Stock Transfers".

**Header row** (flex, justify-between, margin-bottom 20px):
- "Stock Transfers" (page title, already in top bar)
- "+ Transfer" button — background #00352e, white, 40px, radius 8px, Hanken Grotesk 600

**Table card** (white, radius 12px, border 1.5px #e3e8e6, overflow hidden):

Columns: Date | From | To | Status | Action

Header: 11px uppercase #4a6360, padding 11px 16px, background #f9faf7

Rows (padding 14px 16px, border-bottom 1px #f0f0f0, 14px):

Row 1: 09 Ashadh 2083 | Central Warehouse – Balaju | Baneshwor | **Dispatched** (amber pill) | "Mark Received" text-button #00352e 13px underline
Row 2: 09 Ashadh 2083 | Central Warehouse – Balaju | Thamel | Dispatched | Mark Received
Row 3: 08 Ashadh 2083 | Central Warehouse – Balaju | Koteshwor | **Received** (green pill) | —
Row 4: 08 Ashadh 2083 | Central Warehouse – Balaju | Kalanki | Received | —
Row 5: 07 Ashadh 2083 | Central Warehouse – Balaju | Lazimpat | Received | —

Status pills: Dispatched — #fef3c7 bg #92400e text; Received — #dcfce7 bg #166534 text

**New Transfer modal** (420px, white, radius 20px, shadow-xl, padding 28px):
Title "New Transfer" 20px 700
"From location" select: all locations (Central Warehouse default) — 48px, full width
"To location" select: all outlet locations — 48px
Buttons: Cancel + "Dispatch" (#00352e)

---

### PROMPT 12 — Invoices Screen

Design the Tax Invoices screen for Everfresh admin. Sidebar + top bar, page title "Invoices".

**Table card** (white, radius 12px, border 1.5px #e3e8e6, overflow hidden):

Columns: Invoice # | Issued | Customer | Taxable (Rs) | VAT (Rs) | Total (Rs) | CBMS | Action

Header: 11px uppercase #4a6360, padding 11px 16px, background #f9faf7

Rows (padding 12px 16px, border-bottom 1px #f0f0f0, 13px):

Row 1: INV-2083-0042 (JetBrains Mono 13px) | 09 Ashadh 2083 | Hotel Yak & Yeti | 18,000.00 | 2,340.00 | 20,340.00 | **Synced** (green pill) | "Print" link
Row 2: INV-2083-0041 | 09 Ashadh 2083 | Thamel Kitchen Supplies | 8,500.00 | 1,105.00 | 9,605.00 | **Pending** (amber pill) | Print
Row 3: INV-2083-0040 | 08 Ashadh 2083 | Summit Restaurant | 24,000.00 | 3,120.00 | 27,120.00 | Synced | Print
Row 4: INV-2083-0039 | 08 Ashadh 2083 | — (walk-in) | 0 | 0 | 4,200.00 | Synced | Print
Row 5: INV-2083-0038 | 07 Ashadh 2083 | Himalayan Hotel | 32,000.00 | 4,160.00 | 36,160.00 | **Failed** (red pill) | Print

All monetary values: JetBrains Mono 13px, right-aligned
CBMS pills: Synced #dcfce7/#166534, Pending #fef3c7/#92400e, Failed #fee2e2/#b91c1c
"Print" link: 13px, #00352e, underline on hover

Pagination footer: "Showing 1–25 of 312 invoices"

---

### PROMPT 13 — Sales Reports Screen

Design the Sales Reports screen for Everfresh admin. Sidebar + top bar, page title "Sales Reports".

**Filter bar** (white card, radius 12px, border 1.5px #e3e8e6, padding 16px 20px, margin-bottom 20px, flex row gap 16px align-end):
- "From" date input (140px, 40px, border 1.5px #e3e8e6, radius 8px, JetBrains Mono 14px) — placeholder "YYYY-MM-DD"
- "To" date input (same style)
- Label note below each: "(BS date)" in 11px gray

**KPI strip** (2 cards side by side, gap 16px, margin-bottom 20px):
- "Total Orders in Range: 847" (Hanken Grotesk 700, 28px)
- "Revenue in Range: Rs 4,28,200.00" (JetBrains Mono 700, 28px, #00352e)

**Orders table** (white, radius 12px, border 1.5px #e3e8e6, overflow hidden):
Columns: Order # | Date | Outlet | Source | Status | Total

Row 1: #000041 | 09 Ashadh 2083 | Baneshwor | Counter | Fulfilled ✓ | Rs 2,511.00
Row 2: #000040 | 09 Ashadh 2083 | Thamel | Counter | Fulfilled ✓ | Rs 580.00
Row 3: #000039 | 09 Ashadh 2083 | Koteshwor | Counter | Fulfilled ✓ | Rs 4,200.00
Row 4: #000038 | 08 Ashadh 2083 | Lazimpat | Wholesale | Fulfilled ✓ | Rs 36,000.00
Row 5: #000037 | 08 Ashadh 2083 | Counter | App | Fulfilled ✓ | Rs 1,630.00

Source badges: Counter (gray pill), Wholesale (blue pill), App (purple pill), Phone (teal pill)

---

### PROMPT 14 — Lots Management Screen

Design the Lots (live chicken batch) management screen. Sidebar + top bar, page title "Lots".

Header: "+ Lot" button right-aligned, background #00352e, white, 40px.

**Table card:**
Columns: Code | Source | Supplier | Arrival Location | Birds | Weight (kg) | Status | Action

Row 1: LOT-2083-047 (JetBrains Mono) | Own | — | Processing Plant | 420 | 840.000 | **Slaughter** (red pill) | "→ Processing"
Row 2: LOT-2083-046 | External | Pashupati Poultry Farm | Central Warehouse | 350 | 682.500 | **Storage** (gray pill) | —
Row 3: LOT-2083-045 | External | Himalayan Chicken House | Processing Plant | 500 | 975.000 | **Sale** (green pill) | —
Row 4: LOT-2083-044 | Own | — | Processing Plant | 380 | 741.000 | **Settlement** (emerald pill) | —
Row 5: LOT-2083-043 | External | Valley Poultry Suppliers | Central Warehouse | 200 | 390.000 | **Arrival** (blue pill) | —

Status pill colors:
- arrival: #dbeafe/#1d4ed8 — just received
- grading: #fef3c7/#92400e
- storage: #f3f4f6/#374151
- slaughter: #fee2e2/#b91c1c
- packaging: #f3e8ff/#7e22ce
- sale: #dcfce7/#166534
- settlement: #ecfdf5/#059669

Lot code column: JetBrains Mono 13px, #111a18
Weights: JetBrains Mono 13px

**New Lot modal** (480px):
Fields: Lot Code (text), Source (Own / External toggle), Supplier (select, conditional on External), Arrival Location (select), Live Weight kg (number), Bird Count (integer)

---

### PROMPT 15 — Processing Runs Screen

Design the Processing Runs screen showing slaughter/processing operations. Sidebar + top bar, page title "Processing Runs".

Header: "+ Run" button right-aligned.

**Table card:**
Columns: Date | Lot | Input (kg) | Output (kg) | Yield % | Operator

Row 1: 09 Ashadh 2083 | LOT-2083-047 | 840.000 | 672.000 | **80.0%** (green) | Dawa Sherpa
Row 2: 08 Ashadh 2083 | LOT-2083-045 | 975.000 | 780.000 | 80.0% | Ganga Rai
Row 3: 07 Ashadh 2083 | LOT-2083-043 | 390.000 | 304.200 | **78.0%** (amber, below avg) | Dawa Sherpa
Row 4: 06 Ashadh 2083 | LOT-2083-041 | 682.500 | 552.825 | 81.0% (green) | Ganga Rai

Yield coloring: ≥80% green, 75-79% amber, <75% red

Qty values: JetBrains Mono 13px
Yield: JetBrains Mono 600, 13px, with color-coded background pill

**New Run modal** (420px):
Fields: Lot (select — only lots in "slaughter" status), Input Weight kg, Output Weight kg
Auto-calculates and shows yield preview below fields: "Yield: 80.0%" (real-time update)

---

### PROMPT 16 — Procurement Screen

Design the Procurement screen showing purchase orders and goods received. Sidebar + top bar, page title "Procurement".

Two tabs: "Purchase Orders" | "Goods Received" — tab bar below top bar, border-bottom 2px #00352e on active tab.

**Purchase Orders tab:**
Header: "+ Purchase Order" button

Table: # | Date | Supplier | Items | Status | Action
Row 1: PO-2083-012 | 09 Ashadh 2083 | Pashupati Poultry Farm | 420 birds | Open (blue) | "Receive GRN"
Row 2: PO-2083-011 | 08 Ashadh 2083 | Himalayan Chicken House | 500 birds | Received (green) | —
Row 3: PO-2083-010 | 07 Ashadh 2083 | Sunrise Feeds Pvt Ltd | 50 bags feed | Received (green) | —

**Goods Received tab:**
Table: GRN # | Date | PO # | Supplier | Lot | Weight (kg)
Row 1: GRN-047 | 09 Ashadh 2083 | PO-012 | Pashupati Poultry Farm | LOT-2083-047 | 840.000
Row 2: GRN-046 | 08 Ashadh 2083 | PO-011 | Himalayan Chicken House | LOT-2083-045 | 975.000

---

### PROMPT 17 — Users Management Screen

Design the Users management screen for the Everfresh admin superuser. Sidebar + top bar, page title "Users".

Header: "+ Add User" button right-aligned, #00352e.

**Filter bar:** Search input (280px, "Search username or name…") + Role filter select (All / Manager / Outlet Manager / Cashier / Warehouse / Procurement / Customer)

**Table card:**
Columns: Username | Name | Role | Outlet(s) | Status | Action

Row 1: admin | Admin Everfresh | **Superuser** (purple pill) | All | Active (green dot) | Edit
Row 2: om_baneshwor | Rajan Shrestha | **Outlet Manager** (teal pill) | Baneshwor | Active | Edit
Row 3: cashier_baneshwor | Ramesh Oli | **Cashier** (blue pill) | Baneshwor | Active | Edit
Row 4: om_thamel | Sita Tamang | Outlet Manager | Thamel | Active | Edit
Row 5: cashier_thamel | Kabita Poudel | Cashier | Thamel | Active | Edit
Row 6: worker_balaju | Dawa Sherpa | **Warehouse** (amber pill) | Central Warehouse | Active | Edit
Row 7: worker_proc1 | Ganga Rai | Warehouse | Central Warehouse | Active | Edit
(29 total rows, paginated)

Role pill colors: Superuser #f3e8ff/#7e22ce, Manager #dbeafe/#1d4ed8, Outlet Manager #ccfbf1/#0f766e, Cashier #e0f2fe/#0369a1, Warehouse #fef3c7/#92400e, Procurement #fce7f3/#be185d

**Edit User modal** (480px): Username (readonly), First/Last name, Role (select), Assigned Locations (multi-select checkboxes), Password reset button, Active toggle

---

### PROMPT 18 — Customers Screen

Design the Customers screen for Everfresh admin. Sidebar + top bar, page title "Customers".

Header: "+ Add Customer" button.

Filter: Search input + Type filter (All / Retail / Wholesale)

**Table card:**
Columns: Name | Type | PAN | Credit Limit | Balance | Action

Row 1: Hotel Yak & Yeti | **Wholesale** (blue pill) | 302001001 | Rs 5,00,000 | Rs 0 | Edit
Row 2: Thamel Kitchen Supplies | Wholesale | 302001002 | Rs 3,00,000 | Rs 28,000 | Edit
Row 3: Summit Restaurant Pvt Ltd | Wholesale | 302001003 | Rs 4,00,000 | Rs 0 | Edit
Row 4: Himalayan Hotel Catering | Wholesale | 302001004 | Rs 6,00,000 | Rs 0 | Edit
Row 5: Patan Momo House | Wholesale | — | Rs 1,00,000 | Rs 0 | Edit
Row 6: Gongabu Fast Food | **Retail** (gray pill) | — | Rs 0 | Rs 0 | Edit

JetBrains Mono for PAN, credit limit, balance
Credit limit: Rs 0 = no credit (gray); >0 = #166534

---

## GROUP 4 — WORKER PORTAL (Warehouse/Procurement, Mobile-first)

Device for all Worker screens: 390×844 (iPhone 15 Pro size). Single-column layout. No prices, no revenue, no financial data anywhere. Large touch targets (min 56px).

**Worker nav header (shared):**
Background #00352e, 64px tall, padding 0 20px, flex row align-center:
- Back arrow (←) if on sub-screen, white, 40×40px tap target
- Title text white, Hanken Grotesk 700, 18px, centered
- Person icon button top-right for sign out, white, 40×40px

**Bottom tab bar (Worker Home only):**
Background white, border-top 1.5px #e3e8e6, 72px tall:
- Tasks (checkmark icon) | Lot Arrivals | Processing | Receive | Log Out
- Active tab: icon + label in #00352e; inactive: #4a6360

---

### PROMPT 19 — Worker Home Screen

Design the Worker home screen for a warehouse worker at Everfresh (Dawa Sherpa, Central Warehouse). Mobile, 390×844. No financial data.

**Header:** (see shared spec) Title "Everfresh Worker" — static, no back arrow. Right: "Dawa" avatar initials circle 36px, #00352e bg, white text.

**Body** (background #f9faf7, padding 20px, overflow-y scroll):

Greeting card (white, radius 16px, border 1.5px #e3e8e6, padding 20px, margin-bottom 20px):
- "Good morning, Dawa" — Hanken Grotesk 700, 20px
- "Central Warehouse · 09 Ashadh 2083" — 13px, #4a6360

Task cards (vertical stack, gap 12px):

Each task card (white, radius 16px, border 1.5px #e3e8e6, padding 20px, flex row, align-center, 72px min-height, fully tappable):
- Left: colored icon circle 48px
- Center: task title Hanken Grotesk 600, 16px + subtitle 13px #4a6360
- Right: chevron → #4a6360

1. **Record Lot Arrival** (green icon, chicken icon) — "Register new batch arrival"
2. **Enter Processing Run** (amber icon, scissors) — "Log slaughter & processing"
3. **Receive Transfer** (blue icon, box-arrow-in) — "Accept incoming stock" · "2 pending" badge
4. **Record Wastage** (red icon, trash) — "Log spoilage or damage"
5. **View Flock Log** (teal icon, list) — "Check lot status history"

"2 pending" badge on item 3: small red circle with white "2", 20px, top-right of icon

---

### PROMPT 20 — Lot Arrival Entry Screen

Design the Lot Arrival entry screen for a warehouse worker. Mobile, 390×844. No financial data anywhere.

**Header:** Back arrow + "New Lot Arrival"

**Body** (background #f9faf7, padding 20px, scroll):

Progress indicator: "Step 1 of 1 — Batch Details" (linear dots, #00352e active)

Form card (white, radius 16px, border 1.5px #e3e8e6, padding 20px):

Each field (margin-bottom 20px):
- Label 13px 500 #4a6360, margin-bottom 6px
- Input/select 56px height, border 1.5px #e3e8e6, radius 10px, Hanken Grotesk 400 16px, padding 0 16px
- Focus: border 2px #00352e, shadow 0 0 0 3px rgba(0,53,46,0.1)

Fields (in order):
1. **Lot Code** — text, placeholder "LOT-2083-048", keyboard: default
2. **Source** — segment control (Own | External), #00352e active background, white text, 56px tall, full width, 2 equal segments
3. **Supplier** _(shown when External selected)_ — select dropdown, "Select supplier…", options: Pashupati Poultry Farm / Himalayan Chicken House / Valley Poultry Suppliers / etc.
4. **Arrival Location** — select: Central Warehouse – Balaju / Processing Plant – Balaju
5. **Bird Count** — number input, keyboard: numeric, placeholder "420"
6. **Live Weight (kg)** — number input, keyboard: decimal, placeholder "840.000", JetBrains Mono

Note below weight: "💡 Tip: Weigh on certified scale before entry" — 12px, italic, #4a6360

**Footer** (fixed bottom, background white, border-top 1.5px #e3e8e6, padding 16px 20px, safe-area-bottom):
"Save Lot Arrival" button — full width, 56px, background #00352e, white, Hanken Grotesk 700, 16px, radius 12px
Loading: "Saving…" + spinner

Error inline (above button): "Lot code already exists" — red banner, radius 8px

---

### PROMPT 21 — Processing Run Entry Screen

Design the Processing Run entry screen for a warehouse worker logging a slaughter/processing session. Mobile, 390×844. No financial data.

**Header:** Back arrow + "New Processing Run"

**Body** (background #f9faf7, padding 20px, scroll):

Info banner (background #f0faf8, border 1.5px #00352e, radius 10px, padding 14px 16px, margin-bottom 20px):
"🐔 Only lots in 'Slaughter' status are available below."
13px, #00352e

Form card (white, radius 16px, border 1.5px #e3e8e6, padding 20px):

Fields:
1. **Lot** — select dropdown, 56px, "Select lot…"
   Options with status shown: "LOT-2083-047 · 420 birds · 840 kg (Slaughter)"
   Selected shows lot code + bird count summary below in #4a6360 small text

2. **Input Weight (kg)** — number 56px, JetBrains Mono 18px, placeholder "840.000"
   Label hint: "Total weight entering processing"

3. **Output Weight (kg)** — number 56px, JetBrains Mono 18px, placeholder "672.000"
   Label hint: "Dressed weight after processing"

**Live yield preview** (shown when both weights filled):
White row, radius 10px, background #f9faf7, border 1.5px #e3e8e6, padding 14px 16px, margin-top 16px:
"Yield: 80.0%" — Hanken Grotesk 700, 24px, centered
Color: ≥80% #166534, 75-79% #92400e, <75% #b91c1c

**Footer fixed:** "Save Run" button — full width, 56px, #00352e

---

### PROMPT 22 — Receive Transfer Screen

Design the Receive Transfer screen for a warehouse worker accepting incoming stock. Mobile, 390×844.

**Header:** Back arrow + "Receive Transfer"

**Pending transfers list** (if multiple):
Background #f9faf7, padding 20px.

Section header "2 Pending Transfers" — 14px 600 #4a6360, margin-bottom 12px

Each pending transfer card (white, radius 16px, border 1.5px #e3e8e6, padding 18px 20px, margin-bottom 12px, tappable):
- "Transfer #18" — Hanken Grotesk 700, 16px, #111a18
- "From: Central Warehouse – Balaju" — 13px, #4a6360
- "Dispatched: 09 Ashadh 2083" — 13px, #4a6360
- "Chicken Breast · 20.000 kg" — 14px, #111a18 (product summary, NO prices)
- Blue arrow pill "Tap to receive →" — small, right-aligned, 12px, #0369a1

**After tapping a transfer (detail + confirm view):**

Transfer detail card (white, radius 16px, padding 20px, margin-bottom 16px):
- "Transfer #18" — 18px 700
- From/To row: "Central Warehouse → Thamel" — 14px with arrow icon
- Dispatched: 09 Ashadh 2083, 08:30 AM

Items received (no price column):
- Chicken Breast (Boneless) — 20.000 kg
- Whole Chicken (Fresh) — 15.000 kg

"Confirm Receipt" button — full width, 56px, background #00352e, white, 700
"← Back to list" text link below, centered, 14px, #4a6360

Success state: green checkmark circle + "Transfer received successfully!" + "Back to Home" button

---

### PROMPT 23 — Record Wastage Screen

Design the Record Wastage screen for a warehouse worker logging spoilage or damage. Mobile, 390×844. No prices.

**Header:** Back arrow + "Record Wastage"

Warning banner (background #fef2f2, border 1.5px #b91c1c, radius 10px, padding 14px, margin-bottom 20px):
"⚠ Wastage records are permanent and cannot be edited."
13px, #b91c1c

Form card (white, radius 16px, border 1.5px #e3e8e6, padding 20px):

Fields:
1. **Product** — select, 56px, "Select product…" (all products, no prices shown, just names)
2. **Location** — select, 56px (Central Warehouse / Processing Plant)
3. **Qty (kg)** — number, 56px, JetBrains Mono 18px, placeholder "0.000"
4. **Reason** (optional) — textarea, 4 lines, 14px, placeholder "Describe spoilage, damage, or reason for wastage…", resize-none, radius 10px

**Footer fixed:** "Record Wastage" button — full width, 56px, background #b91c1c (danger red), white text, 700
Loading state: "Saving…" spinner

---

### PROMPT 24 — Flock Log Screen

Design the Flock Log screen for a warehouse worker to view lot history and status. Mobile, 390×844. Read-only, no prices.

**Header:** Back arrow + "Flock Log"

**Filter row** (padding 16px 20px, background white, border-bottom 1.5px #e3e8e6):
Status filter: horizontal scroll row of pill buttons (All | Arrival | Grading | Storage | Slaughter | Sale | Settlement)
Each pill: 36px height, radius 20px, Hanken Grotesk 500, 13px
Active: #00352e background white text; inactive: border 1.5px #e3e8e6, text #4a6360

**Lot cards** (background #f9faf7, padding 16px, gap 12px):

Each lot card (white, radius 16px, border 1.5px #e3e8e6, padding 18px 20px):
- Header row: "LOT-2083-047" JetBrains Mono 600 15px #111a18 left + Status pill right
- Row 2: "420 birds · 840.000 kg" — 14px #111a18 (quantities, no money)
- Row 3: "Arrived: 07 Ashadh 2083 · Own" — 13px #4a6360
- Row 4 (if supplier): "Supplier: Pashupati Poultry Farm" — 13px #4a6360
- Row 5: "Location: Processing Plant – Balaju" — 13px #4a6360

Sample cards:
Card 1: LOT-2083-047 | Slaughter (red) | 420 birds · 840.000 kg | Arrived 07 Ashadh 2083
Card 2: LOT-2083-046 | Storage (gray) | 350 birds · 682.500 kg | Arrived 06 Ashadh 2083
Card 3: LOT-2083-045 | Sale (green) | 500 birds · 975.000 kg | Arrived 05 Ashadh 2083
Card 4: LOT-2083-044 | Settlement (emerald) | 380 birds · 741.000 kg | Arrived 04 Ashadh 2083
Card 5: LOT-2083-043 | Arrival (blue) | 200 birds · 390.000 kg | Arrived 09 Ashadh 2083

---

### PROMPT 25 — Audit Log Screen (Admin)

Design the Audit Log screen for Everfresh admin. Shows a read-only chronological log of important system events. Sidebar + top bar, page title "Audit Log".

**Filter bar** (white card, padding 16px 20px, radius 12px, border 1.5px #e3e8e6, margin-bottom 20px, flex row gap 12px):
- Actor (user) filter: select "All Users" / admin / om_baneshwor / cashier_baneshwor / etc.
- Date from / to: two date inputs

**Log table** (white, radius 12px, border 1.5px #e3e8e6, overflow hidden):

Columns: Timestamp | Actor | Action | Object | Detail

Header: 11px uppercase #4a6360, padding 11px 16px, background #f9faf7

Rows (12px, border-bottom 1px #f0f0f0, padding 11px 16px):
- 09 Ashadh 2083 12:31:07 | cashier_baneshwor | CREATE | Order #41 | Rs 2,511 at Baneshwor
- 09 Ashadh 2083 12:30:44 | cashier_baneshwor | CREATE | Payment | Cash Rs 3,000 change Rs 489
- 09 Ashadh 2083 11:15:22 | admin | CREATE | Price | Whole Chicken retail Rs 420 from 09 Ashadh 2083
- 09 Ashadh 2083 09:02:11 | cashier_baneshwor | OPEN SESSION | Session #8 | Float Rs 500
- 08 Ashadh 2083 18:44:03 | cashier_thamel | CLOSE SESSION | Session #7 | Counted Rs 12,500 Variance Rs 0

Timestamps: JetBrains Mono 12px, #4a6360
Actors: Hanken Grotesk 500 #00352e, underline on hover
Actions: pill badges — CREATE green, UPDATE blue, DELETE red, OPEN/CLOSE amber

---

### PROMPT 26 — Settings Screen (Admin)

Design the Settings screen for Everfresh admin (superuser only). Sidebar + top bar, page title "Settings".

**Layout:** Single column, sections separated by category headers, max-width 720px, centered.

**Section 1: Company Info** (white card, radius 12px, border 1.5px #e3e8e6, padding 24px, margin-bottom 20px):
Title: "Company Information" — 16px 600 border-bottom 1.5px #e3e8e6 padding-bottom 14px margin-bottom 20px
Fields:
- Company Name: "Everfresh Poultry Pvt. Ltd." (text input, 48px)
- PAN Number: "123456789" (text, JetBrains Mono)
- Address: "Balaju, Kathmandu, Nepal" (text)
- Phone: "+977-1-4XXXXXX" (text)

**Section 2: Receipt Settings** (same card style):
Title: "Receipt & Invoice"
- Store tagline: "Fresh Every Day"
- Default receipt language (select: English / Nepali)
- Auto-print receipt on sale (toggle, default off)
- Print thermal (80mm) by default (toggle, default on)

**Section 3: Alerts** (same card style):
Title: "Stock Alerts"
- Low stock threshold kg: number input, default 5.000
- Expiry alert days: number input, default 3
- Alert email: text input

**Save Changes** button — background #00352e, white, 48px, full width of form, radius 10px, Hanken Grotesk 700
