#!/bin/bash
# =============================================================================
# setup-new-vps.sh — Full DALIA 2.0 setup on a new VPS
# =============================================================================
#
# WHAT THIS SCRIPT DOES
# ---------------------
# Fully provisions a new VPS from scratch by combining:
#   1. Source code       — cloned from public GitHub repo
#   2. Secrets + config  — pulled from private GitHub repo (overlay/)
#   3. Fuseki RDF data   — restored from a tar archive you copy over manually
#   4. PostgreSQL data   — restored from a pg_dump SQL file you copy over manually
#   5. Media uploads     — restored from a tar archive you copy over manually
#
# WHY FUSEKI/POSTGRES/MEDIA ARE NOT IN GITHUB (not even the private repo)
# -----------------------------------------------------------------------
# GitHub has a hard 100 MB per-file limit and a ~5 GB repo size recommendation.
# Fuseki raw data is 1.6 GB; compressed it is ~85 MB — borderline and growing.
# Git LFS would allow it but requires paid storage quotas on GitHub.
#
# More importantly: database dumps and RDF stores contain live user data (accounts,
# content, sessions). Storing user data in a git repo — even a private one — is a
# GDPR/privacy risk: git history is permanent and hard to purge cleanly.
#
# Git is optimised for text diffs. Binary blobs (postgres dumps, RDF binary files,
# uploaded images) make repos slow to clone and bloat history with every backup.
#
# The correct split is:
#   Git (private repo)  → credentials, config, infrastructure files (small, text)
#   Manual transfer     → database dumps, RDF stores, media uploads (binary, large)
#
# HOW TO USE
# ----------
# On the CURRENT (source) host, run these once to capture current state:
#
#   cd /path/to/dalia20
#   make push-private                                # push .env, traefik/, hosts
#   make backup-db                                   # → backups/backup_YYYYMMDD_HHMMSS.sql
#   podman unshare tar -czf ~/fuseki-data.tar.gz \
#       -C data fuseki                               # Fuseki must use podman unshare (uid 10998)
#   tar -czf ~/media.tar.gz -C . media
#
# Copy the three data files to the new VPS:
#
#   scp ~/fuseki-data.tar.gz ~/media.tar.gz \
#       backups/backup_*.sql \
#       user@NEW-VPS-IP:~/transfer/
#
# On the NEW VPS, install prerequisites:
#
#   # RHEL / Fedora / AlmaLinux
#   sudo dnf install -y podman podman-compose git make rsync python3 python3-dotenv
#
#   # Ubuntu / Debian
#   sudo apt install -y podman podman-compose git make rsync python3 python3-dotenv
#
# Then run this script:
#
#   mkdir -p ~/transfer   # copy data files here first
#   git clone https://github.com/data-literacy-alliance/dalia.git dalia20
#   bash dalia20/scripts/setup-new-vps.sh /opt/dalia20
#                                          ^^^^^^^^^
#                                          install path (default: ~/dalia20)
#
# WHAT TO UPDATE IN .env AFTER SETUP
# ------------------------------------
# After the script finishes, edit dalia20/.env and update:
#
#   ALLOWED_HOSTS        — add the new VPS public IP and/or domain name
#                          e.g. ALLOWED_HOSTS=localhost,127.0.0.1,new-vps-ip,new.domain.com
#
#   NEXT_PUBLIC_API_URL  — only if the public domain differs from search.dalia.education
#                          e.g. NEXT_PUBLIC_API_URL=https://new.domain.com/api/dalia/v1
#
#   CSRF_TRUSTED_ORIGINS — add the new domain
#                          e.g. CSRF_TRUSTED_ORIGINS=https://new.domain.com
#
#   CF_TUNNEL_TOKEN      — if using Cloudflare tunnel on the new VPS, update the token
#                          (each tunnel has its own token from Cloudflare Zero Trust)
#
#   SECRET_KEY           — keep the same value as production if you want existing
#                          sessions to remain valid; generate a new one if migrating
#                          and want a clean break:
#                          python3 -c "import secrets; print(secrets.token_urlsafe(50))"
#
# After editing .env, restart the web container to pick up changes:
#   podman restart dalia20-web
#
# HOSTUID NOTE
# ------------
# Traefik uses the Podman socket at /run/user/${HOSTUID}/podman/podman.sock.
# This script automatically sets HOSTUID to $(id -u) of the user running it.
# If Traefik fails to start, verify:
#   grep HOSTUID "$(find traefik/ -name .env | head -1)"
#   id -u   # must match
#
# =============================================================================

set -euo pipefail

INSTALL_DIR="${1:-$HOME/dalia20}"
TRANSFER_DIR="$HOME/transfer"
PUBLIC_REPO="https://github.com/data-literacy-alliance/dalia.git"
PRIVATE_REPO="https://github.com/data-literacy-alliance/dalia-private-config.git"

echo "============================================================"
echo " DALIA 2.0 — New VPS Setup"
echo " Install dir : $INSTALL_DIR"
echo " Transfer dir: $TRANSFER_DIR"
echo "============================================================"
echo ""

# ── 1. Verify transfer files are present ─────────────────────────
echo "==> [1/13] Checking transfer files ..."
MISSING=0
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
    echo "ERROR: Transfer files missing. Copy them first from the source host:"
    echo ""
    echo "  scp ~/fuseki-data.tar.gz ~/media.tar.gz \\"
    echo "      dalia20/backups/backup_*.sql \\"
    echo "      user@$(hostname):~/transfer/"
    exit 1
fi
echo "  OK — fuseki-data.tar.gz, media.tar.gz, $(basename "$SQL_FILE")"

# ── 2. Required system path for admin-server container ───────────
echo ""
echo "==> [2/13] Creating /opt/container-status (required by traefik admin-server) ..."
sudo mkdir -p /opt/container-status
echo "  OK"

# ── 3. Clone public repo ──────────────────────────────────────────
echo ""
echo "==> [3/13] Cloning public repo → $INSTALL_DIR ..."
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "  Directory already a git repo — pulling latest changes."
    git -C "$INSTALL_DIR" pull --ff-only
elif [ -d "$INSTALL_DIR" ] && [ "$(ls -A "$INSTALL_DIR")" ]; then
    echo "  Non-empty directory already exists — assuming repo already cloned."
else
    git clone "$PUBLIC_REPO" "$INSTALL_DIR"
fi
cd "$INSTALL_DIR"

# ── 4. Restore secrets + traefik config from private repo ────────
echo ""
echo "==> [4/13] Restoring private config overlay ..."
echo "  (secrets in .env, traefik/ config, hosts, host-trigger.py)"
if [ -f ".env" ] && [ -d "traefik" ]; then
    echo "  .env and traefik/ already present — skipping private repo clone."
else
    echo "PRIVATE_REPO=$PRIVATE_REPO" > .syncrc
    make setup-private
fi

# ── 5. Fix HOSTUID for this VPS ──────────────────────────────────
# Traefik mounts the Podman socket at /run/user/$HOSTUID/podman/podman.sock.
# This must match the UID of the user running podman on this VPS.
TRAEFIK_ENV=$(find traefik/ -name ".env" 2>/dev/null | head -1)
echo ""
echo "==> [5/13] Setting HOSTUID=$(id -u) in traefik .env ..."
if grep -q "^HOSTUID=" "$TRAEFIK_ENV" 2>/dev/null; then
    sed -i "s/^HOSTUID=.*/HOSTUID=$(id -u)/" "$TRAEFIK_ENV"
else
    echo "HOSTUID=$(id -u)" >> "$TRAEFIK_ENV"
fi
echo "  OK — HOSTUID=$(id -u)"

# ── 6. Restore Fuseki data ────────────────────────────────────────
# IMPORTANT: Fuseki data is owned by container uid 10998 (not the host user).
# podman unshare maps the container's uid namespace so the files get correct
# ownership inside the Podman user namespace. Without podman unshare the Fuseki
# container cannot read its own data and will start with an empty database.
echo ""
echo "==> [6/13] Restoring Fuseki RDF data (container-owned files — using podman unshare) ..."
mkdir -p data
podman unshare tar -xzf "$TRANSFER_DIR/fuseki-data.tar.gz" -C data/
echo "  OK"

# ── 7. Restore media files ────────────────────────────────────────
echo ""
echo "==> [7/13] Restoring media uploads ..."
tar -xzf "$TRANSFER_DIR/media.tar.gz" -C "$INSTALL_DIR/"
echo "  OK"

# ── 8. Build all containers ───────────────────────────────────────
# Builds web (Django/gunicorn), frontend (Next.js), and fuseki images.
# Does NOT rebuild postgres/redis/elasticsearch — those use stock images.
echo ""
echo "==> [8/13] Building containers — this takes several minutes ..."
make build

# ── 9. Start Traefik first ────────────────────────────────────────
# Traefik MUST start before the app containers because it creates the
# daliaproject_proxy-net Docker network that podman-compose.yml declares
# as external. If app containers start first they will fail with
# "network daliaproject_proxy-net not found".
echo ""
echo "==> [9/13] Starting Traefik (creates daliaproject_proxy-net network) ..."
bash traefik-start.sh

# ── 10. Start app containers ─────────────────────────────────────
echo ""
echo "==> [10/13] Starting app containers ..."
make up

# ── 11. Wait for web container to be ready ───────────────────────
echo ""
echo "==> [11/13] Waiting for dalia20-web to become healthy ..."
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

# ── 12. Restore PostgreSQL database ──────────────────────────────
# pg_dump --clean was used, so the restore DROPs existing tables before
# recreating them. Safe to run even on a freshly migrated database.
echo ""
echo "==> [12/13] Restoring PostgreSQL from $(basename "$SQL_FILE") ..."
make dbrestore BACKUP="$SQL_FILE"

# ── 13. Collect static files ─────────────────────────────────────
# staticfiles/ is not in git (container-owned, rebuilt on each deployment).
echo ""
echo "==> [13/13] Collecting static files ..."
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
