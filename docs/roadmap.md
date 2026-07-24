# Roadmap — extension points beyond Phase 1

What is deliberately not built yet, and where the seams are. Each item lists
the hook in the current code so future work extends rather than rewrites.

## Phase 2 (committed scope, per claude.md)

- **Customer auth flow + mobile app.** `User.customer` FK and the `customer`
  role already exist; customer reads of own orders/invoices are scoped and
  tested (`test_all_roles_access_matrix.py`). Writes are blocked by
  `CustomerReadOnly` in `apps/accounts/permissions.py` — lifting app ordering
  means replacing that guard with a dedicated customer order endpoint
  (Order.source already has an `app` value).
- **Online ordering / nearest-outlet routing.** `Location.lat/lng` and
  `Customer.lat/lng` columns already exist.
- **Loyalty.** Price tier `member` exists in `catalog.PriceTier`; loyalty
  accrual would hang off `Order.customer`.
- **Delivery tracking, full accounting** — greenfield apps; nothing blocks them.

## Open items (from claude.md — still configurable, still not hardcoded)

- VAT registration / per-product taxability: `Product.tax_class` drives the
  tax engine; flip per product when management confirms.
- Lot cost allocation method: `Lot.accumulated_cost_paisa` is a stub.
- CBMS/IRD integration: `cbms_status` fields + sync stub in
  `apps/billing/tasks.py` — swap the stub for the real API client.

## Production-hardening backlog (verified gaps, in rough priority order)

1. **Exports (CSV/PDF).** Not present anywhere. Natural first cut: CSV
     download on `/api/orders/` and `/api/movements/` list views (DRF
     renderer or a `?format=csv` action), PDF for invoices.
2. **Off-host backup copies.** `deploy/backup_db.sh` covers local dumps;
     ship them to object storage (rclone/S3) next.
3. **Metrics.** Sentry (errors) and `/api/health/` (uptime) exist; add
     Prometheus exporters if ops outgrows `docker compose logs`.
4. **Email/notification channel.** Celery low-stock and expiry alerts exist
     as tasks; they currently only write alert rows — wire an email/SMS
     backend when a provider is chosen.
5. **Forgot-password.** Intentionally absent: accounts are admin-created
     (`/admin/users`). Revisit only if staff self-service becomes a need —
     it requires a verified email or SMS channel first (see 4).

## Testing conventions going forward

- Every new endpoint must be added to `LIST_MATRIX` (and, if it writes, to
  `WRITE_DENIALS`) in `apps/accounts/tests/test_all_roles_access_matrix.py`.
  The matrix asserts the full 7-role vector per endpoint, so a missing row
  is a review-visible gap, not a silent hole.
- Run the suite in parallel: `pytest -n auto` (pytest-xdist; CI does this).
- Date-filter tests must use `timezone.localdate(...)`, never
  `timezone.now().date()` — `created_at__date` compares in Asia/Kathmandu,
  and the UTC date is one day behind between 18:15 and 24:00 UTC.
