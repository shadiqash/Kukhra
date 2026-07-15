"""
Role-enforcement DRF permission classes — single source of truth for role checking.
All other apps import from here.

Role matrix (R = read, RW = read+write, -- = no access, own = location-scoped)
-----------
Resource group          superuser  manager  outlet_mgr  cashier  warehouse  procurement  customer
users/system config        RW        RW        --          --        --          --          --
locations (read)           RW        RW        R(own)      R         R           R           --
catalog/products           RW        RW        R           R         R           R           --
catalog/prices             RW        RW        R           R         --          --          --
lots / processing          RW        RW        --          --        RW          RW          --
inventory/movements        RW        RW        R(own)      --        RW          --          --
inventory/transfers        RW        RW        R(own)      --        RW          --          --
procurement (PO/GR)        RW        RW        --          --        --          RW          --
sales (orders/sessions)    RW        RW        R(own)      RW        --          --          R(own)
billing/invoices           RW        RW        R(own)      --        --          --          R(own)
billing/credit-notes       RW        RW        R(own)      --        --          --          --

Rule 7: cashier has NO finance/billing/report access.
         warehouse (worker) has NO money/price/sales access.
Outlet manager: read-only, scoped to assigned_locations. No system settings or user management.
Customer: read-only own orders/invoices (scoped by customer FK).
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS

from .models import Role


def _role_permission(*roles, name='_RolePermission'):
    """Factory: returns a BasePermission subclass that allows exactly the given roles."""
    return type(name, (BasePermission,), {
        'allowed_roles': frozenset(roles),
        'has_permission': lambda self, request, view: (
            bool(request.user and request.user.is_authenticated) and
            request.user.role in self.allowed_roles
        ),
    })


# ── Named permission classes used by viewsets ────────────────────────────────

# System admin operations only (user management, global config).
# Outlet manager is intentionally excluded.
IsManagerOrSuperuser = _role_permission(
    Role.MANAGER, Role.SUPERUSER,
    name='IsManagerOrSuperuser',
)

# Finance write endpoints (Invoice create, InvoiceLine, CreditNote).
# Rule 7: cashier has NO access. Outlet manager gets read-only via IsSalesOrManager below.
IsFinanceStaff = _role_permission(
    Role.MANAGER, Role.SUPERUSER,
    name='IsFinanceStaff',
)

# Sales write endpoints (Session, Order, OrderLine, Payment).
# Outlet manager included — writes are blocked separately via OutletManagerReadOnly.
# Rule 7: warehouse (worker) has NO money/price/sales access.
IsSalesStaff = _role_permission(
    Role.CASHIER, Role.MANAGER, Role.SUPERUSER, Role.OUTLET_MANAGER,
    name='IsSalesStaff',
)

# Production/lot ops (Lots, ProcessingRun).
# Outlet manager excluded — they don't manage production.
IsWarehouseStaff = _role_permission(
    Role.WAREHOUSE, Role.MANAGER, Role.SUPERUSER,
    name='IsWarehouseStaff',
)

# Inventory read/write (StockMovement, StockTransfer, stock query).
# Outlet manager included for read access — writes blocked by OutletManagerReadOnly.
IsInventoryStaff = _role_permission(
    Role.WAREHOUSE, Role.MANAGER, Role.SUPERUSER, Role.OUTLET_MANAGER,
    name='IsInventoryStaff',
)

# Procurement operations (PurchaseOrder, GoodsReceived, Suppliers write).
# Outlet manager excluded.
IsProcurementStaff = _role_permission(
    Role.PROCUREMENT, Role.MANAGER, Role.SUPERUSER,
    name='IsProcurementStaff',
)

# Price read (catalog.Price).
# Cashier needs active prices for POS; outlet manager needs them for reporting.
# Rule 7: warehouse (worker) blocked from money/price endpoints.
IsPriceReader = _role_permission(
    Role.CASHIER, Role.MANAGER, Role.SUPERUSER, Role.OUTLET_MANAGER,
    name='IsPriceReader',
)

# For Order list: cashier, manager, superuser, outlet_manager, customer.
# Outlet manager included — scoped via get_queryset, writes blocked by OutletManagerReadOnly.
IsSalesOrCustomer = _role_permission(
    Role.CASHIER, Role.MANAGER, Role.SUPERUSER, Role.OUTLET_MANAGER, Role.CUSTOMER,
    name='IsSalesOrCustomer',
)

# For Invoice/CreditNote list: Rule 7 — cashier has NO billing access.
# Excludes CASHIER vs IsSalesOrCustomer.
IsInvoiceReader = _role_permission(
    Role.MANAGER, Role.SUPERUSER, Role.OUTLET_MANAGER, Role.CUSTOMER,
    name='IsInvoiceReader',
)

# Aggregate revenue reports (e.g. /orders/summary/).
# Rule 7: cashier has NO finance/report access — a cashier may create orders but
# must never read org-wide takings. Customer excluded: aggregates are not per-customer.
IsReportReader = _role_permission(
    Role.MANAGER, Role.SUPERUSER, Role.OUTLET_MANAGER,
    name='IsReportReader',
)


class OutletManagerReadOnly(BasePermission):
    """
    For viewsets where outlet_manager has read-only access.
    When the requesting user is an outlet_manager, SAFE_METHODS are allowed; writes are denied.
    For all other roles, this permission always passes through (other classes handle their access).
    Pair with IsInventoryStaff / IsSalesStaff / IsSalesOrCustomer which include OUTLET_MANAGER.
    """
    def has_permission(self, request, view):
        if (
            request.user and
            request.user.is_authenticated and
            request.user.role == Role.OUTLET_MANAGER
        ):
            return request.method in SAFE_METHODS
        return True


class ReadOnlyOrManager(BasePermission):
    """
    SAFE_METHODS for any authenticated non-customer staff (including outlet_manager).
    Writes require manager or superuser.
    Used for master-data endpoints (locations, products, partners).
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return request.user.role not in (Role.CUSTOMER,)
        return request.user.role in (Role.MANAGER, Role.SUPERUSER)


class IsCustomerSelf(BasePermission):
    """
    Object-level guard for customer-role users.
    - Non-customer roles: always pass through.
    - Customer role: object must have customer_id == request.user.customer_id.
    Apply to Order and Invoice viewsets in combination with IsSalesOrCustomer.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.user.role != Role.CUSTOMER:
            return True
        customer_id = getattr(request.user, 'customer_id', None)
        if not customer_id:
            return False
        return getattr(obj, 'customer_id', None) == customer_id


# ── Outlet-scoping helper ────────────────────────────────────────────────────

def outlet_location_ids(user):
    """
    Returns a list of Location PKs assigned to an outlet_manager user.
    Returns None for all other roles — callers interpret None as "no location filter".
    """
    if user.is_authenticated and user.role == Role.OUTLET_MANAGER:
        return list(user.assigned_locations.values_list('id', flat=True))
    return None
