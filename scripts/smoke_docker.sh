#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/deploy/docker-compose.server.yml"
ENV_FILE="$ROOT_DIR/deploy/backend.server.env"
DATA_DIR="$ROOT_DIR/deploy/data"
SNAPSHOT_SOURCE="${SNAPSHOT_SOURCE:-$ROOT_DIR/snapshot.db}"

cd "$ROOT_DIR"

if [[ ! -f "$SNAPSHOT_SOURCE" ]]; then
  echo "snapshot.db not found: $SNAPSHOT_SOURCE" >&2
  echo "Set SNAPSHOT_SOURCE=/path/to/snapshot.db or place snapshot.db at repo root." >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  cp "$ROOT_DIR/deploy/backend.server.env.example" "$ENV_FILE"
fi

mkdir -p "$DATA_DIR"
cp "$SNAPSHOT_SOURCE" "$DATA_DIR/snapshot.db"

docker build -t yk-review-agent-backend:session6 .
docker build --build-arg VITE_API_BASE=/api/v1 -t yk-review-agent-frontend:session6 frontend

docker compose -f "$COMPOSE_FILE" up -d

cleanup() {
  docker compose -f "$COMPOSE_FILE" down
}
trap cleanup EXIT

for _ in $(seq 1 30); do
  if curl -fsS http://localhost:18765/api/v1/health >/dev/null; then
    break
  fi
  sleep 2
done

curl -fsS http://localhost:18765/api/v1/health
curl -fsS http://localhost:18088/healthz

echo
echo "Docker smoke passed. Frontend: http://localhost:18088 Backend: http://localhost:18765/api/v1"
