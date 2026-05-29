#!/bin/bash
# export $(grep -v '^#' traefik/.env | xargs)

# This method safely loads your .env file without breaking on special characters
set -a
source traefik/.env
set +a

# Fire and forget
# nohup python3 host-trigger.py > /dev/null 2>&1 &

# Log execution
nohup python3 host-trigger.py > /tmp/host-trigger.log 2>&1 &
echo $! > /tmp/host-trigger.pid

# Print status
echo "Starting traefik and maintenance containers using traefik-compose.yml..."

# Build and start containers using podman-compose
podman-compose -f traefik-compose.yml -p "traefik" up --build -d admin-server
podman-compose -f traefik-compose.yml -p "traefik" up --build -d maintenance-server
podman-compose -f traefik-compose.yml -p "traefik" up --build -d traefik

MAX_RETRIES=10
COUNT=0

while true; do
  # NETWORK_EXISTS=$(podman network exists daliaproject_proxy-net && echo yes || echo no)
  NETWORK_EXISTS=$(podman network exists daliaproject_proxy-net && echo yes || echo no)
  CONTAINER_EXISTS=$(podman ps --filter "name=traefik" --filter "status=running" --format "{{.Names}}" | grep -q traefik && echo yes || echo no)

  if [ "$NETWORK_EXISTS" = "yes" ] && [ "$CONTAINER_EXISTS" = "yes" ]; then
    echo "'proxy-net' is ready and Traefik is running."
    break
  fi

  COUNT=$((COUNT + 1))
  if [ "$COUNT" -ge "$MAX_RETRIES" ]; then
    echo "ERROR: Traefik failed or network 'proxy-net' not ready after $((MAX_RETRIES * 5)) seconds."
    exit 1
  fi

  echo "Waiting... ($COUNT/$MAX_RETRIES)"
  sleep 5
done

echo "'proxy-net' network is now available."

# Optional: Show container status
echo "Container status:"
podman ps