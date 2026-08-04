# Deployment

The full production stack ships as Docker containers: PostgreSQL, Redis,
Django (gunicorn), a Celery worker, Celery beat, and nginx serving the built
React app while proxying `/api/`, `/admin/`, and `/static/` to the backend.

## First deploy

```bash
cp .env.example .env
# Fill in real values. At minimum:
#   DJANGO_SECRET_KEY  — 50+ random chars (python3 -c "import secrets; print(secrets.token_urlsafe(50))")
#   DB_PASSWORD        — strong password (compose refuses to start without it)
#   ALLOWED_HOSTS      — e.g. pos.everfresh.com.np
#   SECURE_SSL_REDIRECT=false  only for LAN-only outlet boxes with no TLS

docker compose -f docker-compose.prod.yml up -d --build
```

Migrations and `collectstatic` run automatically in the backend container's
entrypoint on every start. Create the first superuser once:

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```

## Health & monitoring

- `GET /api/health/` — unauthenticated; returns 200 with `{status: "ok"}`
  when Postgres and Redis are reachable, 503 otherwise. The compose file
  uses it as the backend healthcheck; point external monitoring at it too.
- All logs go to stdout (`docker compose logs -f backend worker beat`).
  `LOG_LEVEL` in `.env` tunes verbosity.
- Set `SENTRY_DSN` to enable error reporting.

## Security posture

- `config/settings/prod.py`: HSTS, secure cookies, SSL redirect (all
  toggled off together by `SECURE_SSL_REDIRECT=false` for LAN deployments),
  `X-Forwarded-Proto` trusted from the nginx proxy.
- The SPA is served with a strict `Content-Security-Policy`
  (`frontend/nginx.conf`): `script-src 'self'`, so an injected inline handler
  cannot execute even if untrusted text reaches the DOM. The Django admin and
  DRF surfaces get a companion CSP from `config.middleware.SecurityHeadersMiddleware`.
- Login endpoint (`/api/auth/token/`) is rate-limited two ways against brute
  force: per client IP (`LOGIN_THROTTLE_RATE`, default 10/min) and per submitted
  username (`LOGIN_USER_THROTTLE_RATE`, default 5/min), so a shared NAT can't
  lock out an outlet and one account can't be sprayed from many IPs. Counts are
  shared across gunicorn workers via the Redis cache. Behind the proxy, set
  `NUM_PROXIES` (default 1) so the per-IP bucket keys on the real client, not nginx.
- The backend container runs as a non-root user.

> **⚠ Plaintext LAN caveat (SECURE_SSL_REDIRECT=false).** In this mode there is
> no TLS, so the JWT bearer tokens the POS sends on every request cross the LAN
> in cleartext and are sniffable by anyone on the segment. Only use it on a
> physically isolated / trusted outlet network (dedicated VLAN, no guest Wi-Fi),
> and prefer terminating TLS (see **TLS** below) even on the LAN where possible.

> **Token storage follow-up.** The SPA currently keeps the access and 7-day
> refresh tokens in `localStorage`. The CSP above caps the XSS blast radius; the
> stronger fix is to move the refresh token into an `HttpOnly; Secure; SameSite`
> cookie with the access token held only in memory. That is an auth-flow change
> (backend sets/reads the cookie, CSRF handling on refresh) and is tracked as a
> follow-up rather than shipped here.

## Backups

`deploy/backup_db.sh` dumps the Postgres container nightly and keeps the
last 14 dumps (tune with `BACKUP_DIR` / `BACKUP_KEEP`). Install it on the
host cron:

```bash
crontab -e
# 30 2 * * * /opt/everfresh/deploy/backup_db.sh >> /var/log/everfresh-backup.log 2>&1
```

Restore instructions are in the script header. Test a restore against a
scratch database after the first backup and then periodically — an untested
backup is not a backup. Copy dumps off the host (object storage, another
machine) so a dead disk doesn't take the backups with it.

## TLS

The bundled nginx listens on plain HTTP (`HTTP_PORT`, default 80). For a
public deployment, terminate TLS in front of it — e.g. a cloud load
balancer, or Caddy/certbot on the host — and forward to `HTTP_PORT`.

## Upgrades

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build   # rebuilds + restarts changed services
```

Postgres data and uploaded media live in the named volumes `postgres_data`
and `media_data`; images are disposable.
