#!/usr/bin/env bash
#
# Everfresh (Kukhra) — bare-metal production bootstrap for a fresh
# Ubuntu 24.04 DigitalOcean droplet.
#
# Installs Python 3.12, PostgreSQL 16, Redis, Nginx, Certbot, Node 20;
# clones the repo, sets up the backend (gunicorn via systemd) and the
# built React frontend (served by nginx), then requests a Let's Encrypt
# cert with certbot --nginx.
#
# Usage: paste this whole script after SSHing in as root (or a sudo user):
#   curl -fsSL <raw-url-to-this-file> -o bootstrap.sh && bash bootstrap.sh
# or paste it directly into the terminal.
#
# Edit the CONFIG block below before running.

set -euo pipefail

# ───────────────────────── CONFIG — edit before running ─────────────────────
REPO_URL="https://github.com/shadiqash/Kukhra.git"
DOMAIN="everfresh.shadiq.tech"
DROPLET_IP="168.144.140.228"
# DNS for $DOMAIN isn't pointed at $DROPLET_IP yet, so this run skips certbot
# and serves plain HTTP on the IP. Once the A record is live, set this to
# true and re-run (or just run the certbot command printed at the end).
ENABLE_HTTPS=false
LETSENCRYPT_EMAIL="shadiqpoke@gmail.com"      # certbot renewal notices
APP_USER="everfresh"                          # unprivileged system user for the app
APP_DIR="/opt/everfresh"
DB_NAME="everfresh"
DB_USER="everfresh"
DB_PASSWORD="$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 32)"
DJANGO_SECRET_KEY="$(openssl rand -base64 50 | tr -dc 'a-zA-Z0-9' | head -c 50)"
GUNICORN_WORKERS=3
# ──────────────────────────────────────────────────────────────────────────

if [[ $EUID -ne 0 ]]; then
  echo "Run this as root (or with sudo -E)." >&2
  exit 1
fi

echo "==> Updating apt and installing base packages"
apt-get update
apt-get install -y --no-install-recommends \
  software-properties-common ca-certificates curl gnupg git build-essential \
  libpq-dev

echo "==> Installing Python 3.12"
add-apt-repository -y ppa:deadsnakes/ppa
apt-get update
apt-get install -y python3.12 python3.12-venv python3.12-dev

echo "==> Installing PostgreSQL 16"
install -d /usr/share/postgresql-common/pgdg
curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
  -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc
echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] \
http://apt.postgresql.org/pub/repos/apt $(. /etc/os-release && echo "$VERSION_CODENAME")-pgdg main" \
  > /etc/apt/sources.list.d/pgdg.list
apt-get update
apt-get install -y postgresql-16

echo "==> Installing Redis"
apt-get install -y redis-server
systemctl enable --now redis-server

echo "==> Installing Nginx and Certbot"
apt-get install -y nginx certbot python3-certbot-nginx

echo "==> Installing Node 20"
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs

echo "==> Creating system user ${APP_USER}"
id -u "${APP_USER}" &>/dev/null || useradd --system --create-home --shell /bin/bash "${APP_USER}"

echo "==> Creating PostgreSQL role and database"
sudo -u postgres psql -v ON_ERROR_STOP=1 <<-EOSQL
    DO \$\$
    BEGIN
      IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${DB_USER}') THEN
        CREATE ROLE ${DB_USER} WITH LOGIN PASSWORD '${DB_PASSWORD}';
      END IF;
    END
    \$\$;
    SELECT 'CREATE DATABASE ${DB_NAME} OWNER ${DB_USER}'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${DB_NAME}')\gexec
EOSQL

echo "==> Cloning repo into ${APP_DIR}"
if [[ -d "${APP_DIR}/.git" ]]; then
  sudo -u "${APP_USER}" git -C "${APP_DIR}" pull
else
  git clone "${REPO_URL}" "${APP_DIR}"
  chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"
fi

echo "==> Creating venv and installing requirements/prod.txt"
sudo -u "${APP_USER}" python3.12 -m venv "${APP_DIR}/venv"
sudo -u "${APP_USER}" "${APP_DIR}/venv/bin/pip" install --upgrade pip
sudo -u "${APP_USER}" "${APP_DIR}/venv/bin/pip" install -r "${APP_DIR}/requirements/prod.txt"

echo "==> Writing production .env"
cat > "${APP_DIR}/.env" <<-EOF
DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}
DJANGO_SETTINGS_MODULE=config.settings.prod

DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}
DB_HOST=localhost
DB_PORT=5432

REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

MEDIA_ROOT=${APP_DIR}/media

JWT_ACCESS_TOKEN_LIFETIME_MINUTES=60
JWT_REFRESH_TOKEN_LIFETIME_DAYS=7

CORS_ALLOWED_ORIGINS=https://${DOMAIN},http://${DROPLET_IP}

ALLOWED_HOSTS=${DOMAIN},${DROPLET_IP}
SENTRY_DSN=
CSRF_TRUSTED_ORIGINS=https://${DOMAIN},http://${DROPLET_IP}
LOGIN_THROTTLE_RATE=10/min
LOG_LEVEL=INFO
DB_CONN_MAX_AGE=60
SECURE_SSL_REDIRECT=${ENABLE_HTTPS}
EOF
chown "${APP_USER}:${APP_USER}" "${APP_DIR}/.env"
chmod 600 "${APP_DIR}/.env"

echo "==> Running migrations, seed data, and collectstatic"
sudo -u "${APP_USER}" bash -c "
  set -a; source '${APP_DIR}/.env'; set +a
  cd '${APP_DIR}'
  ./venv/bin/python manage.py migrate --noinput
  ./venv/bin/python scripts/seed_data.py
  ./venv/bin/python manage.py collectstatic --noinput
"

echo "==> Building React frontend"
sudo -u "${APP_USER}" bash -c "
  cd '${APP_DIR}/frontend'
  npm ci
  npm run build
"

echo "==> Configuring gunicorn systemd service"
cat > /etc/systemd/system/everfresh-gunicorn.service <<-EOF
[Unit]
Description=Everfresh gunicorn daemon
After=network.target postgresql.service redis-server.service

[Service]
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
ExecStart=${APP_DIR}/venv/bin/gunicorn config.wsgi:application \\
  --bind 127.0.0.1:8000 \\
  --workers ${GUNICORN_WORKERS} \\
  --timeout 60 \\
  --access-logfile - \\
  --error-logfile -
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now everfresh-gunicorn

echo "==> Configuring nginx"
cat > /etc/nginx/sites-available/everfresh <<-EOF
server {
    listen 80;
    server_name ${DOMAIN} ${DROPLET_IP};

    root ${APP_DIR}/frontend/dist;
    index index.html;

    gzip on;
    gzip_types text/css application/javascript application/json image/svg+xml;
    gzip_min_length 1024;

    client_max_body_size 10m;

    # Hashed build assets are immutable — cache for a year.
    location /assets/ {
        add_header Cache-Control "public, max-age=31536000, immutable";
        try_files \$uri =404;
    }

    # API, Django admin, and whitenoise-served static go to gunicorn.
    location ~ ^/(api|admin|static)/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 60s;
    }

    # SPA fallback: every other route serves the React app.
    location / {
        add_header Cache-Control "no-cache";
        try_files \$uri /index.html;
    }
}
EOF

ln -sf /etc/nginx/sites-available/everfresh /etc/nginx/sites-enabled/everfresh
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

if [[ "${ENABLE_HTTPS}" == "true" ]]; then
  echo "==> Requesting HTTPS certificate"
  certbot --nginx -d "${DOMAIN}" -m "${LETSENCRYPT_EMAIL}" --agree-tos --redirect --non-interactive
else
  echo "==> Skipping certbot (ENABLE_HTTPS=false — DNS for ${DOMAIN} not pointed at ${DROPLET_IP} yet)"
  echo "    Once the A record is live, run on the droplet:"
  echo "      certbot --nginx -d ${DOMAIN} -m ${LETSENCRYPT_EMAIL} --agree-tos --redirect --non-interactive"
  echo "    then set SECURE_SSL_REDIRECT=true in ${APP_DIR}/.env and restart everfresh-gunicorn."
fi

echo "==> Done"
echo "App is reachable at: http://${DROPLET_IP}/"
echo "DB password:      ${DB_PASSWORD}"
echo "Django secret key: ${DJANGO_SECRET_KEY}"
echo "(both are saved in ${APP_DIR}/.env — back that file up somewhere safe)"
echo
echo "Create a superuser with:"
echo "  sudo -u ${APP_USER} bash -c \"cd ${APP_DIR} && set -a; source .env; set +a; ./venv/bin/python manage.py createsuperuser\""
