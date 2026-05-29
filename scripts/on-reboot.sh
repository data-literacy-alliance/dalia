#!/bin/bash
# on-reboot.sh — started by @reboot cron job to bring up Traefik + dalia20.
# Uses BASH_SOURCE to find its own location so this works regardless of where
# the project is deployed or if the folder is renamed.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

log "=== dalia20 reboot startup ==="
log "Project dir: $PROJECT_DIR"
cd "$PROJECT_DIR"

# Start Traefik (creates daliaproject_proxy-net network required by nginx)
log "Starting Traefik..."
if bash ./traefik-start.sh; then
    log "Traefik started OK"
else
    log "WARNING: traefik-start.sh exited with errors — continuing anyway"
fi

# Start dalia20 containers
log "Starting dalia20 containers..."
/usr/bin/make up

log "=== Startup complete ==="
