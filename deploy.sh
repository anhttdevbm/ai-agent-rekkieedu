#!/usr/bin/env bash
set -euo pipefail

# Agent Edu deploy helper (production)
# Usage (on server):
#   1) Copy this repo to server (or git clone)
#   2) Create .env with OPENROUTER_API_KEY (required)
#   3) Ensure TLS certs exist at /etc/letsencrypt/live/rikkei.rugal.vn/
#   4) Run: ./deploy.sh
#
# Optional env:
#   PROJECT_DIR=/opt/agent-edu
#   ENV_FILE=.env
#   COMPOSE_FILE=docker-compose.prod.yml
#   DOMAIN=rikkei.rugal.vn

PROJECT_DIR="${PROJECT_DIR:-$(pwd)}"
ENV_FILE="${ENV_FILE:-.env}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
DOMAIN="${DOMAIN:-rikkei.rugal.vn}"

cd "$PROJECT_DIR"

echo "[deploy] Project dir: $PROJECT_DIR"
echo "[deploy] Compose file: $COMPOSE_FILE"
echo "[deploy] Env file: $ENV_FILE"

if ! command -v docker >/dev/null 2>&1; then
  echo "[deploy] ERROR: docker not found. Install Docker first." >&2
  exit 2
fi

if ! docker info >/dev/null 2>&1; then
  echo "[deploy] ERROR: Docker daemon not running or permission denied." >&2
  echo "[deploy] Tip: try 'sudo systemctl start docker' or add user to docker group." >&2
  exit 2
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "[deploy] ERROR: docker compose not available. Install Docker Compose v2." >&2
  exit 2
fi

if [ ! -f "$COMPOSE_FILE" ]; then
  echo "[deploy] ERROR: missing $COMPOSE_FILE" >&2
  exit 2
fi

if [ ! -f "$ENV_FILE" ]; then
  echo "[deploy] ERROR: missing $ENV_FILE" >&2
  echo "[deploy] Create it with at least: OPENROUTER_API_KEY=..." >&2
  exit 2
fi

# Quick validation for required env keys
if ! grep -qE '^\s*OPENROUTER_API_KEY\s*=' "$ENV_FILE"; then
  echo "[deploy] ERROR: OPENROUTER_API_KEY is missing in $ENV_FILE" >&2
  exit 2
fi

echo "[deploy] Pulling base images…"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" pull --ignore-pull-failures || true

echo "[deploy] Building + starting services…"
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --build

echo "[deploy] Waiting for healthcheck (/api/meta)…"
set +e
for i in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1/api/meta" >/dev/null 2>&1; then
    echo "[deploy] OK: service is responding locally (via nginx)."
    set -e
    echo "[deploy] Public URL: https://$DOMAIN"
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps
    exit 0
  fi
  sleep 2
done
set -e

echo "[deploy] ERROR: service did not become healthy in time." >&2
echo "[deploy] Showing recent logs…" >&2
docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs --tail=200 >&2 || true
exit 1

