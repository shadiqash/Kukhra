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
- Login endpoint (`/api/auth/token/`) is throttled to `LOGIN_THROTTLE_RATE`
  (default 10/min per IP) against brute force; counts are shared across
  gunicorn workers via the Redis cache.
- The backend container runs as a non-root user.

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
