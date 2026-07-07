#!/usr/bin/env python3
"""
Seed realistic demo data for Everfresh Poultry Management System.

Run from project root:
    python3 scripts/seed_data.py

Safe to re-run — uses get_or_create throughout.
"""
import os
import sys
import django
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from django.utils import timezone
from apps.accounts.models import User, Role
from apps.catalog.models import Product, Price, TaxClass
from apps.locations.models import Location, LocationType, Counter
from apps.partners.models import Supplier, Customer, SupplierType, CustomerType

now = timezone.now()

print("=" * 60)
print("Everfresh Seed Data")
print("=" * 60)


# ── Locations ──────────────────────────────────────────────────────────────
WAREHOUSE_NAME   = "Central Warehouse – Balaju"
PRODUCTION_NAME  = "Processing Plant – Balaju"

OUTLETS = [
    ("Everfresh Baneshwor",    "baneshwor"),
    ("Everfresh Lazimpat",     "lazimpat"),
    ("Everfresh Thamel",       "thamel"),
    ("Everfresh Koteshwor",    "koteshwor"),
    ("Everfresh Kalanki",      "kalanki"),
    ("Everfresh Chabahil",     "chabahil"),
    ("Everfresh Bhaktapur",    "bhaktapur"),
    ("Everfresh Jawalakhel",   "jawalakhel"),
    ("Everfresh Pulchowk",     "pulchowk"),
    ("Everfresh Sanepa",       "sanepa"),
    ("Everfresh Gongabu",      "gongabu"),
    ("Everfresh Boudha",       "boudha"),
]

warehouse, _ = Location.objects.get_or_create(
    name=WAREHOUSE_NAME,
    defaults={"type": LocationType.WAREHOUSE},
)
print(f"  Warehouse: {warehouse.name}")

production, _ = Location.objects.get_or_create(
    name=PRODUCTION_NAME,
    defaults={"type": LocationType.PRODUCTION},
)
print(f"  Production: {production.name}")

outlets = []
for (name, slug) in OUTLETS:
    loc, _ = Location.objects.get_or_create(
        name=name,
        defaults={"type": LocationType.OUTLET},
    )
    outlets.append(loc)
print(f"  Outlets: {len(outlets)} created/verified")

# Create one counter per outlet
counters = []
for outlet in outlets:
    c, _ = Counter.objects.get_or_create(
        name=f"{outlet.name} Counter",
        defaults={"location": outlet},
    )
    counters.append(c)
print(f"  Counters: {len(counters)}")


# ── Suppliers ──────────────────────────────────────────────────────────────
SUPPLIERS = [
    ("Pashupati Poultry Farm",   SupplierType.FARM,     "300011001"),
    ("Himalayan Chicken House",  SupplierType.FARM,     "300011002"),
    ("Sunrise Feeds Pvt Ltd",    SupplierType.FEED,     "300012001"),
    ("AgriVet Medicine Store",   SupplierType.MEDICINE, "300013001"),
    ("Valley Poultry Suppliers", SupplierType.FARM,     "300011003"),
]
supplier_objs = []
for (name, stype, pan) in SUPPLIERS:
    s, _ = Supplier.objects.get_or_create(name=name, defaults={"type": stype, "pan": pan})
    supplier_objs.append(s)
print(f"  Suppliers: {len(supplier_objs)}")


# ── Products ───────────────────────────────────────────────────────────────
# (name, barcode, uom, is_weighed, tax_class)
PRODUCTS = [
    # Whole bird
    ("Whole Chicken (Fresh)",      "8901030001", "kg",    True,  TaxClass.EXEMPT),
    ("Whole Chicken (Dressed)",    "8901030002", "kg",    True,  TaxClass.EXEMPT),
    ("Country Chicken (Deshi)",    "8901030003", "kg",    True,  TaxClass.EXEMPT),
    # Cuts
    ("Chicken Breast (Boneless)",  "8901030010", "kg",    True,  TaxClass.EXEMPT),
    ("Chicken Leg Quarter",        "8901030011", "kg",    True,  TaxClass.EXEMPT),
    ("Chicken Wing",               "8901030012", "kg",    True,  TaxClass.EXEMPT),
    ("Chicken Thigh (Bone-in)",    "8901030013", "kg",    True,  TaxClass.EXEMPT),
    ("Chicken Liver",              "8901030014", "kg",    True,  TaxClass.EXEMPT),
    ("Chicken Gizzard",            "8901030015", "kg",    True,  TaxClass.EXEMPT),
    ("Chicken Feet",               "8901030016", "kg",    True,  TaxClass.EXEMPT),
    ("Chicken Neck",               "8901030017", "kg",    True,  TaxClass.EXEMPT),
    # Processed / packaged (VAT applicable)
    ("Chicken Sausage 500g",       "8901030020", "piece", False, TaxClass.TAXABLE),
    ("Chicken Momo (Frozen) 300g", "8901030021", "piece", False, TaxClass.TAXABLE),
    ("Marinated Chicken Tikka",    "8901030022", "kg",    True,  TaxClass.TAXABLE),
    ("Chicken Keema (Minced)",     "8901030023", "kg",    True,  TaxClass.EXEMPT),
    # By-products
    ("Egg (Tray 30 pcs)",          "8901030030", "piece", False, TaxClass.EXEMPT),
    ("Chicken Stock Bones",        "8901030031", "kg",    True,  TaxClass.EXEMPT),
    # Premium
    ("Organic Chicken (Whole)",    "8901030040", "kg",    True,  TaxClass.EXEMPT),
    ("Smoked Chicken Breast",      "8901030041", "kg",    True,  TaxClass.TAXABLE),
    ("Chicken Burger Patty 4pk",   "8901030042", "piece", False, TaxClass.TAXABLE),
]

# Retail prices (paisa) — roughly realistic NRS
RETAIL_PRICES = {
    "Whole Chicken (Fresh)":      42000,
    "Whole Chicken (Dressed)":    45000,
    "Country Chicken (Deshi)":    85000,
    "Chicken Breast (Boneless)":  58000,
    "Chicken Leg Quarter":        38000,
    "Chicken Wing":               33000,
    "Chicken Thigh (Bone-in)":    40000,
    "Chicken Liver":              25000,
    "Chicken Gizzard":            22000,
    "Chicken Feet":               15000,
    "Chicken Neck":               12000,
    "Chicken Sausage 500g":       39000,
    "Chicken Momo (Frozen) 300g": 28000,
    "Marinated Chicken Tikka":    62000,
    "Chicken Keema (Minced)":     45000,
    "Egg (Tray 30 pcs)":          60000,
    "Chicken Stock Bones":         8000,
    "Organic Chicken (Whole)":    75000,
    "Smoked Chicken Breast":      72000,
    "Chicken Burger Patty 4pk":   45000,
}
# Wholesale is 10% cheaper
WHOLESALE_DISCOUNT = Decimal("0.90")

product_objs = []
for (name, barcode, uom, is_weighed, tax_class) in PRODUCTS:
    p, created = Product.objects.get_or_create(
        barcode=barcode,
        defaults={
            "name": name,
            "uom": uom,
            "is_weighed": is_weighed,
            "tax_class": tax_class,
        },
    )
    product_objs.append(p)

    retail_paisa = RETAIL_PRICES.get(name, 40000)
    wholesale_paisa = int(retail_paisa * WHOLESALE_DISCOUNT)

    # Retail price
    if not Price.objects.filter(product=p, tier="retail", valid_to__isnull=True).exists():
        Price.objects.create(
            product=p, tier="retail",
            price_paisa=retail_paisa,
            valid_from=now.date(),
        )
    # Wholesale price
    if not Price.objects.filter(product=p, tier="wholesale", valid_to__isnull=True).exists():
        Price.objects.create(
            product=p, tier="wholesale",
            price_paisa=wholesale_paisa,
            valid_from=now.date(),
        )

print(f"  Products: {len(product_objs)} with retail + wholesale prices")


# ── Customers ──────────────────────────────────────────────────────────────
CUSTOMERS = [
    ("Hotel Yak & Yeti",          CustomerType.WHOLESALE, "302001001", 500_000_00),
    ("Thamel Kitchen Supplies",   CustomerType.WHOLESALE, "302001002", 300_000_00),
    ("Summit Restaurant Pvt Ltd", CustomerType.WHOLESALE, "302001003", 400_000_00),
    ("Himalayan Hotel Catering",  CustomerType.WHOLESALE, "302001004", 600_000_00),
    ("Everest Caterers",          CustomerType.WHOLESALE, "302001005", 200_000_00),
    ("Patan Momo House",          CustomerType.WHOLESALE, None,        100_000_00),
    ("Newari Kitchen Banquet",    CustomerType.WHOLESALE, "302001007", 250_000_00),
    ("Gongabu Fast Food",         CustomerType.RETAIL,    None,               0),
    ("Bhaktapur Canteen",         CustomerType.RETAIL,    None,               0),
    ("Sanepa Diner",              CustomerType.RETAIL,    None,               0),
]
customer_objs = []
for (name, ctype, pan, credit) in CUSTOMERS:
    c, _ = Customer.objects.get_or_create(
        name=name,
        defaults={"type": ctype, "pan": pan, "credit_limit_paisa": credit},
    )
    customer_objs.append(c)
print(f"  Customers: {len(customer_objs)}")


# ── Staff accounts ─────────────────────────────────────────────────────────
def make_user(username, password, role, first_name="", last_name="", assigned=None):
    u, created = User.objects.get_or_create(
        username=username,
        defaults={
            "first_name": first_name or username.title(),
            "last_name":  last_name,
            "role":       role,
            "is_staff":   role in (Role.SUPERUSER,),
            "is_superuser": role == Role.SUPERUSER,
        },
    )
    if created:
        u.set_password(password)
        u.save()
        if assigned:
            u.assigned_locations.set(assigned)
    return u, created

# Admin
make_user("admin", "admin123", Role.SUPERUSER, "Admin", "Everfresh")
print("  Admin: admin / admin123")

# Outlet managers — one per outlet
MANAGER_NAMES = [
    ("Rajan", "Shrestha"),  ("Sita", "Tamang"),   ("Hari", "Magar"),
    ("Sunita", "Gurung"),   ("Bikash", "Rai"),     ("Puja", "Thapa"),
    ("Nabin", "KC"),        ("Anita", "Dhakal"),   ("Sujan", "Lama"),
    ("Nisha", "Adhikari"),  ("Prabin", "Basnet"),  ("Manisha", "Bhatta"),
]
for i, (outlet, (fn, ln)) in enumerate(zip(outlets, MANAGER_NAMES)):
    slug = outlet.name.split()[-1].lower()
    u, created = make_user(
        f"om_{slug}", "pass1234", Role.OUTLET_MANAGER,
        fn, ln, assigned=[outlet],
    )
print(f"  Outlet managers: {len(outlets)}")

# Cashiers — one per outlet
CASHIER_NAMES = [
    ("Ramesh", "Oli"),     ("Kabita", "Poudel"),  ("Anil", "Joshi"),
    ("Priya", "Subedi"),   ("Dipak", "Karki"),    ("Sarita", "Bista"),
    ("Roshan", "Dahal"),   ("Durga", "Aryal"),    ("Bijay", "Pandey"),
    ("Mina", "Koirala"),   ("Sandip", "Chaudhary"), ("Rekha", "Bhandari"),
]
for i, (outlet, counter, (fn, ln)) in enumerate(zip(outlets, counters, CASHIER_NAMES)):
    slug = outlet.name.split()[-1].lower()
    u, created = make_user(
        f"cashier_{slug}", "pass1234", Role.CASHIER,
        fn, ln, assigned=[outlet],
    )
print(f"  Cashiers: {len(outlets)}")

# Warehouse/processing workers
WORKERS = [
    ("worker_balaju",    "Dawa",   "Sherpa",    Role.WAREHOUSE),
    ("worker_proc1",     "Ganga",  "Rai",       Role.WAREHOUSE),
    ("worker_quality",   "Binod",  "Thapa",     Role.PROCUREMENT),
    ("worker_logistics", "Kumari", "Maharjan",  Role.PROCUREMENT),
]
for (uname, fn, ln, role) in WORKERS:
    make_user(uname, "pass1234", role, fn, ln, assigned=[warehouse])
print(f"  Workers: {len(WORKERS)}")

print()
print("=" * 60)
print("Seed complete!")
print()
print("Login credentials:")
print("  Admin:           admin / admin123")
print("  Outlet managers: om_<outlet> / pass1234  (e.g. om_baneshwor)")
print("  Cashiers:        cashier_<outlet> / pass1234")
print("  Workers:         worker_balaju / pass1234  etc.")
print("=" * 60)
