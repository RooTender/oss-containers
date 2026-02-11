#!/usr/bin/env bash
set -e

NETWORK="gateway-net"

echo "Checking docker network..."

if ! docker network inspect "$NETWORK" >/dev/null 2>&1; then
  echo "Creating network: $NETWORK"
  docker network create "$NETWORK"
else
  echo "Network exists: $NETWORK"
fi

echo
echo "Starting gateway..."
docker compose up -d

echo
echo "Ensuring Caddy internal CA is trusted..."

CADDY_CONTAINER=$(docker compose ps -q gateway)

if [ -n "$CADDY_CONTAINER" ]; then
  docker exec "$CADDY_CONTAINER" caddy trust || true
  echo "Caddy trust ensured."
else
  echo "Caddy container not found, skipping trust."
fi

echo
echo "Starting services..."

for dir in */ ; do
  if [ -f "$dir/docker-compose.yaml" ]; then
    echo "→ Starting $dir"
    (cd "$dir" && docker compose up -d)
  fi
done

echo
echo "All services started."
