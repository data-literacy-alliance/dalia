#!/bin/bash
# =============================================================================
# setup-local-vps.sh — DALIA 2.0 setup assuming all files are already local
# =============================================================================
#
# Use this instead of setup-new-vps.sh when:
#   - The code is already present in INSTALL_DIR (no git access needed)
#   - .env and traefik/ are already in INSTALL_DIR
#   - Transfer files (fuseki, media, sql) are already in ~/transfer/
#
# HOW TO USE
# ----------
#   bash dalia20/scripts/setup-local-vps.sh /opt/dalia20
#
# =============================================================================

set -euo pipefail

INSTALL_DIR="${1:-$HOME/dalia20}"
TRANSFER_DIR="$HOME/transfer"

echo "============================================================"
echo " DALIA 2.0 — Local VPS Setup (no git)"
echo " Install dir : $INSTALL_DIR"
echo " Transfer dir: $TRANSFER_DIR"
echo "============================================================"
echo ""

# ── 1. Verify install dir has required files ─────────────────────
echo "==> [1/11] Checking local files ..."
MISSING=0
for f in "$INSTALL_DIR/.env" "$INSTALL_DIR/Makefile" "$INSTALL_DIR/traefik-compose.yml" "$INSTALL_DIR/traefik-start.sh"; do
    if [ ! -f "$f" ]; then
        echo "  MISSING: $f"
        MISSING=1
    fi
done
if [ ! -d "$INSTALL_DIR/traefik" ]; then
    echo "  MISSING: $INSTALL_DIR/traefik/"
    MISSING=1
fi
for f in "$TRANSFER_DIR/fuseki-data.tar.gz" "$TRANSFER_DIR/media.tar.gz"; do
    if [ ! -f "$f" ]; then
        echo "  MISSING: $f"
        MISSING=1
    fi
done
SQL_FILE=$(ls "$TRANSFER_DIR"/backup_*.sql 2>/dev/null | head -1 || true)
if [ -z "$SQL_FILE" ]; then
    echo "  MISSING: $TRANSFER_DIR/backup_*.sql"
    MISSING=1
fi
if [ "$MISSING" -eq 1 ]; then
    echo ""
    echo "ERROR: Required files missing. Ensure INSTALL_DIR has code + .env + traefik/"
    echo "       + traefik-compose.yml + traefik-start.sh"
    echo "       and TRANSFER_DIR has fuseki-data.tar.gz, media.tar.gz, backup_*.sql"
    exit 1
fi
echo "  OK — all required files present"

# ── 2. Required system path for admin-server container ───────────
echo ""
echo "==> [2/11] Creating /opt/container-status (required by traefik admin-server) ..."
sudo mkdir -p /opt/container-status
echo "  OK"

cd "$INSTALL_DIR"

# ── 3. Fix HOSTUID for this VPS ──────────────────────────────────
TRAEFIK_ENV=$(find traefik/ -name ".env" 2>/dev/null | head -1)
echo ""
echo "==> [3/11] Setting HOSTUID=$(id -u) in traefik .env ..."
if [ -z "$TRAEFIK_ENV" ]; then
    echo "  WARNING: No traefik .env found — skipping HOSTUID update."
elif grep -q "^HOSTUID=" "$TRAEFIK_ENV" 2>/dev/null; then
    sed -i "s/^HOSTUID=.*/HOSTUID=$(id -u)/" "$TRAEFIK_ENV"
    echo "  OK — HOSTUID=$(id -u) in $TRAEFIK_ENV"
else
    echo "HOSTUID=$(id -u)" >> "$TRAEFIK_ENV"
    echo "  OK — HOSTUID=$(id -u) appended to $TRAEFIK_ENV"
fi

# ── 4. Restore Fuseki data ────────────────────────────────────────
echo ""
echo "==> [4/11] Restoring Fuseki RDF data (using podman unshare) ..."
mkdir -p data
podman unshare tar -xzf "$TRANSFER_DIR/fuseki-data.tar.gz" -C data/
echo "  OK"

# ── 5. Restore media files ────────────────────────────────────────
echo ""
echo "==> [5/11] Restoring media uploads ..."
if [ -d "$INSTALL_DIR/media" ]; then
    echo "  Removing existing media/ (may be container-owned) ..."
    rm -rf "$INSTALL_DIR/media" 2>/dev/null || podman unshare rm -rf "$INSTALL_DIR/media"
fi
tar --no-same-permissions --no-same-owner -xzf "$TRANSFER_DIR/media.tar.gz" -C "$INSTALL_DIR/"
echo "  OK"

# ── 6. Pre-create proxy network + build containers ───────────────
echo ""
echo "==> [6/11] Pre-creating proxy network then building containers ..."
podman network create --subnet 10.89.0.0/24 daliaproject_proxy-net 2>/dev/null || true
podman-compose build --no-cache

# ── 7. Start Traefik first ────────────────────────────────────────
echo ""
echo "==> [7/11] Starting Traefik (creates daliaproject_proxy-net network) ..."
# Traefik reads routes through the podman socket; lingering keeps it alive after logout/reboot.
sudo loginctl enable-linger "$(id -un)" || echo "  WARNING: could not enable lingering"
systemctl --user enable --now podman.socket || echo "  WARNING: could not enable podman.socket"
bash traefik-start.sh

# ── 8. Start app containers ──────────────────────────────────────
echo ""
echo "==> [8/11] Starting app containers ..."
make up

# ── 9. Wait for web container to be ready ────────────────────────
echo ""
echo "==> [9/11] Waiting for dalia20-web to become healthy ..."
READY=0
for i in $(seq 1 30); do
    if podman exec dalia20-web python manage.py check 2>/dev/null | grep -q "System check identified no issues"; then
        echo "  Ready after $((i * 2))s"
        READY=1
        break
    fi
    sleep 2
done
if [ "$READY" -eq 0 ]; then
    echo "  WARNING: web container did not report healthy after 60s — proceeding anyway."
    echo "  Check logs: podman logs dalia20-web"
fi

# ── 10. Restore PostgreSQL database ──────────────────────────────
echo ""
echo "==> [10/11] Restoring PostgreSQL from $(basename "$SQL_FILE") ..."
make dbrestore BACKUP="$SQL_FILE"

# ── 11. Collect static files ─────────────────────────────────────
echo ""
echo "==> [11/11] Collecting static files ..."
podman exec dalia20-web python manage.py collectstatic --noinput

# ── Summary ───────────────────────────────────────────────────────
echo ""
echo "============================================================"
echo " SETUP COMPLETE"
echo "============================================================"
echo ""
echo " Install dir : $INSTALL_DIR"
echo " HOSTUID     : $(id -u)"
echo ""
echo " Running containers:"
podman ps --format "  {{.Names}}  {{.Status}}"
echo ""
echo " !! ACTION REQUIRED — update .env before going live:"
echo ""
echo "    $INSTALL_DIR/.env"
echo ""
echo "    ALLOWED_HOSTS        → add this VPS IP/hostname"
echo "    NEXT_PUBLIC_API_URL  → update if domain differs from search.dalia.education"
echo "    CSRF_TRUSTED_ORIGINS → add new domain"
echo "    CF_TUNNEL_TOKEN      → replace with tunnel token for this VPS (Cloudflare Zero Trust)"
echo ""
echo "    After editing .env:"
echo "      podman restart dalia20-web"
echo ""
echo " Verify the app is responding:"
echo "   curl http://localhost:52080/"
echo ""
echo " For Cloudflare tunnel:"
echo "   make up-tunnel"
echo ""
