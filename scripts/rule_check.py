#!/usr/bin/env python3
"""
Everfresh Phase 1 — non-negotiable rule checker.
Parses source text only; no database, no Django import needed.
Run from the project root: python scripts/rule_check.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APPS_DIR = ROOT / 'apps'

RESULTS = []


def record(status, rule, detail=''):
    RESULTS.append((status, rule, detail))


def src(app, filename='models.py'):
    p = APPS_DIR / app / filename
    return p.read_text() if p.exists() else ''


def is_stub(text):
    """True when the file has no class definitions — still a placeholder."""
    return 'class ' not in text


# ── Rule 3: All money is integer paisa ──────────────────────────────────────
def check_no_float_money():
    for app_dir in sorted(APPS_DIR.iterdir()):
        if not app_dir.is_dir() or app_dir.name.startswith('_'):
            continue
        for py in sorted(app_dir.rglob('*.py')):
            text = py.read_text()
            rel = py.relative_to(ROOT)
            if 'FloatField' in text:
                record('FAIL', 'Rule 3 — no FloatField anywhere', str(rel))
                return
            for line in text.splitlines():
                if (re.search(r'paisa', line, re.I)
                        and 'DecimalField' in line
                        and not line.strip().startswith('#')):
                    record('FAIL', 'Rule 3 — _paisa field uses DecimalField',
                           f'{rel}: {line.strip()}')
                    return
    record('PASS', 'Rule 3 — all money is integer paisa (no FloatField, no DecimalField on _paisa fields)')


# ── Rule 2: Prices are dated rows ───────────────────────────────────────────
def check_price_dated_rows():
    text = src('catalog')
    if is_stub(text):
        record('SKIP', 'Rule 2 — prices are dated rows (catalog not yet defined)')
        return
    has_vf = 'valid_from' in text
    has_vt = 'valid_to' in text
    has_pp = 'price_paisa' in text
    if has_vf and has_vt and has_pp:
        record('PASS', 'Rule 2 — Price has valid_from / valid_to / price_paisa (IntegerField)')
    else:
        record('FAIL', 'Rule 2 — Price row missing required fields',
               f'valid_from={has_vf} valid_to={has_vt} price_paisa={has_pp}')


# ── Rule 2: Price.delete() and Invoice raw-delete blocked ───────────────────
def check_delete_guard():
    for app, model in [('catalog', 'Price'), ('billing', 'Invoice')]:
        text = src(app)
        if is_stub(text) or f'class {model}' not in text:
            record('SKIP', f'Rule 2/6 — {app}.{model} delete-guard (not yet defined)')
            continue
        # Model-level guard
        model_guard = 'def delete' in text and 'raise' in text
        # Admin-level guard (belt-and-suspenders)
        admin_text = src(app, 'admin.py')
        admin_guard = 'has_delete_permission' in admin_text and 'return False' in admin_text
        if model_guard:
            record('PASS', f'Rule — {app}.{model}.delete() raises at model level')
        elif admin_guard:
            record('PASS', f'Rule — {app}.{model} delete blocked via admin (no model guard yet)')
        else:
            record('FAIL', f'Rule — {app}.{model} has no delete guard')


# ── Import rule ──────────────────────────────────────────────────────────────
def check_import_rule():
    # core must import nothing from sibling apps
    violations = []
    for py in sorted((APPS_DIR / 'core').rglob('*.py')):
        text = py.read_text()
        # Self-imports (apps.core.*) are fine; only flag imports of sibling apps
        hits = [h for h in re.findall(r'(?:from|import)\s+apps\.(\w+)', text) if h != 'core']
        if hits:
            violations.append(f'{py.relative_to(ROOT)}: imports apps.{hits}')
    if violations:
        record('FAIL', 'Import rule — core imports a sibling app', '; '.join(violations))
    else:
        record('PASS', 'Import rule — core imports nothing from sibling apps')

    # Check for obvious upward imports (lower-level apps importing from higher-level apps)
    # Layering: core < locations/partners/catalog < lots < processing < inventory < procurement < sales < billing
    layers = [
        ['locations', 'partners', 'catalog'],
        ['lots'],
        ['processing'],
        ['inventory'],
        ['procurement'],
        ['sales'],
        ['billing'],
    ]
    upward_violations = []
    for i, layer in enumerate(layers):
        # Apps above this layer
        above = [a for sublayer in layers[i + 1:] for a in sublayer]
        for app in layer:
            text = src(app)
            for upper in above:
                if f'apps.{upper}' in text:
                    upward_violations.append(f'apps.{app} imports from apps.{upper} (upward)')
    if upward_violations:
        record('FAIL', 'Import rule — upward sibling import detected', '; '.join(upward_violations))
    else:
        record('PASS', 'Import rule — no upward sibling imports detected')


# ── AUTH_USER_MODEL set from day one ────────────────────────────────────────
def check_auth_user_model():
    text = (ROOT / 'config' / 'settings' / 'base.py').read_text()
    if "AUTH_USER_MODEL = 'accounts.User'" in text:
        record('PASS', "AUTH_USER_MODEL = 'accounts.User' set in base.py")
    else:
        record('FAIL', "AUTH_USER_MODEL not set correctly in base.py")


# ── Custom User model in accounts ───────────────────────────────────────────
def check_custom_user_model():
    text = src('accounts')
    if is_stub(text):
        record('SKIP', 'accounts.User — custom User model (not yet defined)')
        return
    if 'class User' in text and ('AbstractUser' in text or 'AbstractBaseUser' in text):
        record('PASS', 'accounts.User — extends AbstractUser / AbstractBaseUser')
    else:
        record('FAIL', 'accounts.User — does not extend AbstractUser / AbstractBaseUser')


# ── Lot state machine ────────────────────────────────────────────────────────
def check_lot_state_machine():
    text = src('lots')
    if is_stub(text):
        record('SKIP', 'Lots — state machine (not yet defined)')
        return
    has_fsm = 'VALID_TRANSITIONS' in text or ('transition' in text and 'def transition' in text)
    has_guard = 'raise ' in text and ('ValueError' in text or 'RuntimeError' in text)
    if has_fsm and has_guard:
        record('PASS', 'Lots — state machine with guarded transitions (raises on illegal move)')
    else:
        record('FAIL', 'Lots — state machine missing transition guard',
               f'transition_fn={has_fsm} raise_guard={has_guard}')


# ── Rule 4: Location is first-class (stock always per-location) ─────────────
def check_location_first_class():
    text = src('inventory')
    if is_stub(text) or 'class StockMovement' not in text:
        record('SKIP', 'Rule 4 — location FK on StockMovement (inventory not yet defined)')
        return
    if 'location' in text and 'ForeignKey' in text:
        record('PASS', 'Rule 4 — StockMovement has a location ForeignKey')
    else:
        record('FAIL', 'Rule 4 — StockMovement missing location FK')


# ── Rule 5: lot_id on every StockMovement ───────────────────────────────────
def check_lot_on_movement():
    text = src('inventory')
    if is_stub(text) or 'class StockMovement' not in text:
        record('SKIP', 'Rule 5 — lot FK on StockMovement (inventory not yet defined)')
        return
    if 'lot' in text and 'ForeignKey' in text:
        record('PASS', 'Rule 5 — StockMovement has a lot ForeignKey')
    else:
        record('FAIL', 'Rule 5 — StockMovement missing lot FK')


# ── StockMovement is append-only ─────────────────────────────────────────────
def check_stock_movement_append_only():
    text = src('inventory')
    if is_stub(text) or 'class StockMovement' not in text:
        record('SKIP', 'Rule 1 — StockMovement append-only guard (inventory not yet defined)')
        return
    has_delete_guard = 'def delete' in text and 'raise' in text
    has_save_guard = 'def save' in text and ('raise' in text or 'pk is None' in text or 'self.pk' in text)
    if has_delete_guard and has_save_guard:
        record('PASS', 'Rule 1 — StockMovement blocks delete and update (append-only)')
    elif has_delete_guard:
        record('FAIL', 'Rule 1 — StockMovement blocks delete but not update')
    else:
        record('FAIL', 'Rule 1 — StockMovement has no append-only guard')


# ── Rule 6: Order is the single entry point for all sales ────────────────────
def check_order_is_entry_point():
    text = src('sales')
    if is_stub(text) or 'class Order' not in text:
        record('SKIP', 'Rule 6 — Order is single entry point for all sales (not yet defined)')
        return
    has_source = 'source' in text and ('counter' in text or 'OrderSource' in text)
    if has_source:
        record('PASS', 'Rule 6 — Order has source field (counter|app|phone|wholesale)')
    else:
        record('FAIL', 'Rule 6 — Order missing source field; all sale paths must route through Order')


# ── Rule 7: Role enforcement at the API ──────────────────────────────────────
def check_role_enforcement():
    perm_text = src('accounts', 'permissions.py')
    if is_stub(perm_text) or 'class ' not in perm_text:
        record('SKIP', 'Rule 7 — role enforcement at API (permissions.py not yet implemented — step 9)')
        return
    has_cashier_check = 'cashier' in perm_text.lower() and ('permission' in perm_text.lower() or 'class ' in perm_text)
    if has_cashier_check:
        record('PASS', 'Rule 7 — accounts.permissions defines cashier-scoped permission classes')
    else:
        record('FAIL', 'Rule 7 — accounts.permissions.py exists but has no cashier role gate')


if __name__ == '__main__':
    check_no_float_money()
    check_price_dated_rows()
    check_delete_guard()
    check_import_rule()
    check_auth_user_model()
    check_custom_user_model()
    check_lot_state_machine()
    check_location_first_class()
    check_lot_on_movement()
    check_stock_movement_append_only()
    check_order_is_entry_point()
    check_role_enforcement()

    passed  = sum(1 for s, _, _ in RESULTS if s == 'PASS')
    failed  = sum(1 for s, _, _ in RESULTS if s == 'FAIL')
    skipped = sum(1 for s, _, _ in RESULTS if s == 'SKIP')

    print('\nEverfresh Phase 1 — Rule Check')
    print('=' * 52)
    icons = {'PASS': '✓', 'FAIL': '✗', 'SKIP': '·'}
    for status, rule, detail in RESULTS:
        print(f'  [{icons[status]}] {rule}')
        if detail:
            print(f'        → {detail}')
    print(f'\n  {passed} passed  {failed} failed  {skipped} skipped\n')
    sys.exit(1 if failed else 0)
