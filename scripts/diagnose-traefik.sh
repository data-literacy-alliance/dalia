#!/bin/bash
# =============================================================================
# diagnose-traefik.sh — DALIA 2.0 Traefik routing diagnostic
# =============================================================================
#
# Validates the complete Traefik routing chain on a VPS and identifies why
# a domain may not reach the correct container.
#
# HOW TO USE
# ----------
#   bash dalia20/scripts/diagnose-traefik.sh [INSTALL_DIR] [EXPECTED_HOSTNAME]
#
#   INSTALL_DIR      — path where dalia20 is installed (default: /opt/dalia20)
#   EXPECTED_HOSTNAME — the domain to diagnose (default: search-dev.dalia.education)
#
# EXAMPLES
#   bash dalia20/scripts/diagnose-traefik.sh
#   bash dalia20/scripts/diagnose-traefik.sh /opt/dalia20 search.dalia.education
#
# =============================================================================

set -uo pipefail

INSTALL_DIR="${1:-/opt/dalia20}"
EXPECTED_HOST="${2:-search-dev.dalia.education}"
TRAEFIK_ENV="$INSTALL_DIR/traefik/git.rwth-aachen.de/rpdm/vulcanus/devcontainers/traefik/.env"
DYNAMIC_YML="$INSTALL_DIR/traefik/git.rwth-aachen.de/rpdm/vulcanus/devcontainers/traefik/dynamic.yml"
COMPOSE_YML="$INSTALL_DIR/podman-compose.yml"

EXPECTED_NETWORK="daliaproject_proxy-net"
EXPECTED_SUBNET="10.89.0.0/24"
EXPECTED_PORT=52080
TRAEFIK_API_PORT=8080

PASS=0
WARN=0
FAIL=0
FIXES=()

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GRN='\033[0;32m'
YLW='\033[0;33m'
BLU='\033[0;34m'
CYN='\033[0;36m'
RST='\033[0m'
BOLD='\033[1m'

ok()   { echo -e "  ${GRN}PASS${RST}  $1"; PASS=$((PASS+1)); }
warn() { echo -e "  ${YLW}WARN${RST}  $1"; WARN=$((WARN+1)); FIXES+=("WARN: $2"); }
fail() { echo -e "  ${RED}FAIL${RST}  $1"; FAIL=$((FAIL+1)); FIXES+=("FAIL: $2"); }
info() { echo -e "  ${BLU}INFO${RST}  $1"; }
hdr()  { echo -e "\n${BOLD}${CYN}── $1 ──────────────────────────────────────────────────────────${RST}"; }

echo ""
echo -e "${BOLD}DALIA 2.0 — Traefik Routing Diagnostic${RST}"
echo -e "  Install dir : $INSTALL_DIR"
echo -e "  Expected host: $EXPECTED_HOST"
echo ""

# =============================================================================
# 1. INSTALL DIR
# =============================================================================
hdr "1. Install Directory"

if [ -d "$INSTALL_DIR" ]; then
    ok "Install dir exists: $INSTALL_DIR"
else
    fail "Install dir missing: $INSTALL_DIR" "Create or specify correct INSTALL_DIR"
    echo -e "\n${RED}Cannot continue without install dir. Exiting.${RST}"
    exit 1
fi

# =============================================================================
# 2. CRITICAL CONFIG FILES
# =============================================================================
hdr "2. Config Files"

for f in "$TRAEFIK_ENV" "$DYNAMIC_YML" "$COMPOSE_YML" \
         "$INSTALL_DIR/traefik-compose.yml" \
         "$INSTALL_DIR/traefik-start.sh" \
         "$INSTALL_DIR/.env"; do
    if [ -f "$f" ]; then
        ok "$(basename "$f")  →  $f"
    else
        fail "Missing: $f" "Copy $f from private config overlay before running"
    fi
done

# =============================================================================
# 3. HOSTUID
# =============================================================================
hdr "3. HOSTUID (Podman socket path)"

ACTUAL_UID=$(id -u)
CONFIGURED_UID=""
if [ -f "$TRAEFIK_ENV" ]; then
    CONFIGURED_UID=$(grep "^HOSTUID=" "$TRAEFIK_ENV" | cut -d= -f2 | tr -d '"' | tr -d "'")
fi

info "Current user UID : $ACTUAL_UID"
info "Configured HOSTUID: $CONFIGURED_UID"

if [ "$CONFIGURED_UID" = "$ACTUAL_UID" ]; then
    ok "HOSTUID matches actual UID ($ACTUAL_UID)"
else
    fail "HOSTUID mismatch: traefik .env has '$CONFIGURED_UID', actual UID is '$ACTUAL_UID'" \
         "Run: sed -i 's/^HOSTUID=.*/HOSTUID=$ACTUAL_UID/' $TRAEFIK_ENV  then restart traefik"
fi

SOCKET_PATH="/run/user/$ACTUAL_UID/podman/podman.sock"
if [ -S "$SOCKET_PATH" ]; then
    ok "Podman socket exists: $SOCKET_PATH"
else
    warn "Podman socket not found at $SOCKET_PATH (may still be bound by podman-compose)" \
         "Run: systemctl --user start podman.socket  OR accept that podman-compose binds it directly"
fi

# =============================================================================
# 4. NETWORK
# =============================================================================
hdr "4. Proxy Network"

if podman network exists "$EXPECTED_NETWORK" 2>/dev/null; then
    ACTUAL_SUBNET=$(podman network inspect "$EXPECTED_NETWORK" \
        --format '{{range .Subnets}}{{.Subnet}}{{end}}' 2>/dev/null || echo "unknown")
    info "Network $EXPECTED_NETWORK exists, subnet: $ACTUAL_SUBNET"
    if [ "$ACTUAL_SUBNET" = "$EXPECTED_SUBNET" ]; then
        ok "Subnet correct: $ACTUAL_SUBNET"
    else
        fail "Wrong subnet: '$ACTUAL_SUBNET' (expected $EXPECTED_SUBNET)" \
             "Run: podman network rm --force $EXPECTED_NETWORK && bash $INSTALL_DIR/traefik-start.sh"
    fi
else
    fail "Network $EXPECTED_NETWORK does not exist" \
         "Run: bash $INSTALL_DIR/traefik-start.sh  — it creates the network"
fi

# =============================================================================
# 5. CONTAINERS
# =============================================================================
hdr "5. Running Containers"

REQUIRED_CONTAINERS=(
    "traefik_traefik_1"
    "dalia20-nginx"
    "dalia20-web"
    "dalia20-db"
    "dalia20-redis"
    "dalia20-fuseki"
    "dalia20-elasticsearch"
)

RUNNING=$(podman ps --format "{{.Names}}" 2>/dev/null)

for c in "${REQUIRED_CONTAINERS[@]}"; do
    if echo "$RUNNING" | grep -q "^${c}$"; then
        ok "Container running: $c"
    else
        if [ "$c" = "dalia20-nginx" ]; then
            fail "Container NOT running: $c (CRITICAL — this is the Traefik backend)" \
                 "Run: cd $INSTALL_DIR && podman-compose up -d nginx"
        elif [ "$c" = "traefik_traefik_1" ]; then
            fail "Container NOT running: $c (CRITICAL — Traefik itself is down)" \
                 "Run: bash $INSTALL_DIR/traefik-start.sh"
        else
            warn "Container NOT running: $c" \
                 "Run: cd $INSTALL_DIR && podman-compose up -d"
        fi
    fi
done

# =============================================================================
# 6. NGINX CONTAINER NETWORK MEMBERSHIP
# =============================================================================
hdr "6. nginx Network Membership"

if echo "$RUNNING" | grep -q "^dalia20-nginx$"; then
    NGINX_NETS=$(podman inspect dalia20-nginx \
        --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}' 2>/dev/null | tr ' ' '\n' | grep -v '^$')
    info "dalia20-nginx networks: $(echo "$NGINX_NETS" | tr '\n' ' ')"

    if echo "$NGINX_NETS" | grep -q "$EXPECTED_NETWORK"; then
        ok "nginx is on $EXPECTED_NETWORK"
    else
        fail "nginx is NOT on $EXPECTED_NETWORK — Traefik cannot route to it" \
             "Verify podman-compose.yml nginx service lists $EXPECTED_NETWORK in networks:"
    fi
else
    info "nginx not running — skipping network membership check"
fi

# =============================================================================
# 7. NGINX STATIC IP ON PROXY NET
# =============================================================================
hdr "7. nginx IP on Proxy Network"

if echo "$RUNNING" | grep -q "^dalia20-nginx$" && \
   podman inspect dalia20-nginx --format "{{.NetworkSettings.Networks}}" 2>/dev/null | grep -q "$EXPECTED_NETWORK"; then
    NGINX_IP=$(podman inspect dalia20-nginx \
        --format "{{(index .NetworkSettings.Networks \"$EXPECTED_NETWORK\").IPAddress}}" 2>/dev/null || echo "")
    if [ -n "$NGINX_IP" ]; then
        ok "nginx IP on $EXPECTED_NETWORK: $NGINX_IP"
        info "Traefik will route to http://$NGINX_IP:80 (via docker provider discovery)"
    else
        warn "Could not determine nginx IP on $EXPECTED_NETWORK" \
             "Inspect manually: podman inspect dalia20-nginx"
    fi
fi

# =============================================================================
# 8. NGINX CONTAINER LABELS (Docker provider route)
# =============================================================================
hdr "8. nginx Traefik Labels (Docker Provider Route)"

if echo "$RUNNING" | grep -q "^dalia20-nginx$"; then
    NGINX_LABELS=$(podman inspect dalia20-nginx \
        --format '{{range $k, $v := .Config.Labels}}{{$k}}={{$v}}\n{{end}}' 2>/dev/null | grep "traefik")
    echo ""
    echo "$NGINX_LABELS" | while IFS= read -r label; do
        info "  label: $label"
    done
    echo ""

    NGINX_RULE=$(echo "$NGINX_LABELS" | grep "\.rule=" | sed 's/.*\.rule=//' | tr -d "'" | tr -d '"')
    if [ -z "$NGINX_RULE" ]; then
        fail "nginx has no traefik router rule label" \
             "Check podman-compose.yml nginx labels section"
    else
        info "nginx router rule: $NGINX_RULE"
        if echo "$NGINX_RULE" | grep -q "HostRegexp"; then
            PATTERN=$(echo "$NGINX_RULE" | grep -oP "(?<=HostRegexp\()[^\)]*" | tr -d '`')
            if echo "$EXPECTED_HOST" | grep -qP "$PATTERN" 2>/dev/null; then
                ok "HostRegexp pattern '$PATTERN' matches $EXPECTED_HOST"
            else
                fail "HostRegexp pattern '$PATTERN' does NOT match '$EXPECTED_HOST'" \
                     "Edit $INSTALL_DIR/podman-compose.yml nginx labels:
       Change: traefik.http.routers.dalia20-nginx.rule=HostRegexp(\`$PATTERN\`)
           To: traefik.http.routers.dalia20-nginx.rule=Host(\`$EXPECTED_HOST\`)
       Then restart: cd $INSTALL_DIR && podman-compose up -d nginx"
            fi
        elif echo "$NGINX_RULE" | grep -q "Host("; then
            HOST_IN_RULE=$(echo "$NGINX_RULE" | grep -oP "(?<=Host\()[^\)]*" | tr -d '`' | tr -d "'" | tr -d '"')
            if [ "$HOST_IN_RULE" = "$EXPECTED_HOST" ]; then
                ok "Host rule matches: Host('$EXPECTED_HOST')"
            else
                fail "Host rule mismatch: rule has '$HOST_IN_RULE', expected '$EXPECTED_HOST'" \
                     "Edit podman-compose.yml nginx label to use Host(\`$EXPECTED_HOST\`)"
            fi
        else
            warn "Unrecognized rule format: $NGINX_RULE" \
                 "Verify rule matches $EXPECTED_HOST"
        fi
    fi

    NGINX_ENABLED=$(echo "$NGINX_LABELS" | grep "traefik.enable=" | cut -d= -f2)
    if [ "$NGINX_ENABLED" = "true" ]; then
        ok "traefik.enable=true on nginx"
    else
        fail "traefik.enable is not 'true' on nginx container" \
             "Add label traefik.enable=true to nginx in podman-compose.yml"
    fi

    NGINX_DOCKER_NET=$(echo "$NGINX_LABELS" | grep "traefik.docker.network=" | cut -d= -f2)
    if [ "$NGINX_DOCKER_NET" = "$EXPECTED_NETWORK" ]; then
        ok "traefik.docker.network=$EXPECTED_NETWORK"
    else
        warn "traefik.docker.network='$NGINX_DOCKER_NET' (expected '$EXPECTED_NETWORK')" \
             "Set label: traefik.docker.network=$EXPECTED_NETWORK in podman-compose.yml nginx"
    fi
else
    info "nginx not running — skipping label checks"
fi

# =============================================================================
# 9. DYNAMIC.YML FILE PROVIDER RULES
# =============================================================================
hdr "9. dynamic.yml File Provider Rules"

if [ -f "$DYNAMIC_YML" ]; then
    echo ""
    grep -n "rule:\|HostRegexp\|Host(" "$DYNAMIC_YML" | while IFS= read -r line; do
        info "  $line"
    done
    echo ""

    MAINTENANCE_RULES=$(grep "rule:" "$DYNAMIC_YML" | grep -oP "(?<=rule: \").*(?=\")")
    MAINTENANCE_MATCH=0
    while IFS= read -r rule; do
        if echo "$rule" | grep -q "HostRegexp"; then
            PATTERN=$(echo "$rule" | grep -oP "(?<=HostRegexp\()[^\)]*" | tr -d '`')
            if echo "$EXPECTED_HOST" | grep -qP "$PATTERN" 2>/dev/null; then
                MAINTENANCE_MATCH=1
            fi
        elif echo "$rule" | grep -q "Host("; then
            HOST_VAL=$(echo "$rule" | grep -oP "(?<=Host\()[^\)]*" | tr -d '`' | tr -d "'" | tr -d '"')
            if [ "$HOST_VAL" = "$EXPECTED_HOST" ] || echo "$HOST_VAL" | grep -q "$EXPECTED_HOST"; then
                MAINTENANCE_MATCH=1
            fi
        fi
    done <<< "$MAINTENANCE_RULES"

    if [ "$MAINTENANCE_MATCH" -eq 1 ]; then
        warn "dynamic.yml maintenance rules match $EXPECTED_HOST — maintenance page may appear at /maintenance.html" \
             "Update dynamic.yml maintenance rules if you changed the nginx rule to Host('$EXPECTED_HOST'):
       maintenance-router-specific rule: Host(\`$EXPECTED_HOST\`) && Path(\`/maintenance.html\`)
       maintenance-router-default rule: Host(\`$EXPECTED_HOST\`)"
    else
        info "dynamic.yml maintenance rules do NOT match $EXPECTED_HOST (this is fine if nginx rule is correct)"
    fi
else
    fail "dynamic.yml not found at $DYNAMIC_YML" \
         "Copy dynamic.yml from private config overlay"
fi

# =============================================================================
# 10. TRAEFIK API — REGISTERED ROUTERS
# =============================================================================
hdr "10. Traefik API — Registered Routers"

if curl -s "http://localhost:$TRAEFIK_API_PORT/api/http/routers" --connect-timeout 3 >/dev/null 2>&1; then
    ROUTERS_JSON=$(curl -s "http://localhost:$TRAEFIK_API_PORT/api/http/routers" 2>/dev/null)
    if echo "$ROUTERS_JSON" | python3 -c "import sys,json; json.load(sys.stdin)" 2>/dev/null; then
        ROUTER_COUNT=$(echo "$ROUTERS_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d))" 2>/dev/null || echo "?")
        info "Total registered routers: $ROUTER_COUNT"
        echo ""

        echo "$ROUTERS_JSON" | python3 -c "
import sys, json
routers = json.load(sys.stdin)
expected = sys.argv[1] if len(sys.argv) > 1 else ''
for r in routers:
    name = r.get('name', '?')
    rule = r.get('rule', '?')
    status = r.get('status', '?')
    service = r.get('service', '?')
    priority = r.get('priority', 0)
    print(f'  [{status}] {name}')
    print(f'         rule    : {rule}')
    print(f'         service : {service}')
    print(f'         priority: {priority}')
    print()
" "$EXPECTED_HOST" 2>/dev/null || echo "$ROUTERS_JSON" | python3 -m json.tool 2>/dev/null | head -80

        echo ""
        # Check if any router rule matches expected host
        MATCH_FOUND=$(echo "$ROUTERS_JSON" | python3 -c "
import sys, json, re
routers = json.load(sys.stdin)
expected = '$EXPECTED_HOST'
matched = []
for r in routers:
    rule = r.get('rule', '')
    # Check Host() exact match
    m = re.search(r\"Host\(\`?['\\\"]?([^'\\\"\`\)]+)['\\\"\`]?\)\", rule)
    if m and m.group(1) == expected:
        matched.append(r.get('name'))
        continue
    # Check HostRegexp
    m = re.search(r\"HostRegexp\(\`?['\\\"]?([^'\\\"\`\)]+)['\\\"\`]?\)\", rule)
    if m:
        try:
            if re.match(m.group(1), expected):
                matched.append(r.get('name'))
        except: pass
print(','.join(matched) if matched else '')
" 2>/dev/null || echo "")

        if [ -n "$MATCH_FOUND" ]; then
            ok "Router(s) matching $EXPECTED_HOST: $MATCH_FOUND"
        else
            fail "No router rule matches $EXPECTED_HOST — Traefik will 404 all requests to this host" \
                 "Fix the nginx label in podman-compose.yml to: Host(\`$EXPECTED_HOST\`)
     then restart nginx: cd $INSTALL_DIR && podman-compose up -d nginx"
        fi
    else
        warn "Traefik API returned non-JSON response" \
             "Check: curl http://localhost:$TRAEFIK_API_PORT/api/http/routers"
    fi
else
    warn "Traefik API not reachable at localhost:$TRAEFIK_API_PORT" \
         "Check if traefik is running and dashboard port is exposed: podman ps | grep traefik"
fi

# =============================================================================
# 11. PORT 52080 LISTENING
# =============================================================================
hdr "11. Port $EXPECTED_PORT (Traefik entrypoint)"

if ss -tlnp 2>/dev/null | grep -q ":$EXPECTED_PORT " || \
   netstat -tlnp 2>/dev/null | grep -q ":$EXPECTED_PORT "; then
    ok "Port $EXPECTED_PORT is listening"
else
    fail "Port $EXPECTED_PORT is NOT listening" \
         "Traefik is not running or not bound to this port. Run: bash $INSTALL_DIR/traefik-start.sh"
fi

# =============================================================================
# 12. LIVE ROUTING TEST
# =============================================================================
hdr "12. Live Routing Test (curl with Host header)"

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Host: $EXPECTED_HOST" \
    "http://localhost:$EXPECTED_PORT/" \
    --connect-timeout 5 2>/dev/null || echo "000")

info "curl http://localhost:$EXPECTED_PORT/ -H 'Host: $EXPECTED_HOST' → HTTP $HTTP_CODE"

case "$HTTP_CODE" in
    200|301|302)
        ok "Traefik routes $EXPECTED_HOST correctly (HTTP $HTTP_CODE)"
        ;;
    404)
        fail "HTTP 404 — Traefik reached but no router matches $EXPECTED_HOST" \
             "Fix nginx label or restart nginx after fixing podman-compose.yml"
        ;;
    502|503)
        warn "HTTP $HTTP_CODE — Router exists but backend (nginx) is unreachable" \
             "Check nginx container: podman logs dalia20-nginx --tail 20"
        ;;
    000)
        fail "Could not connect to localhost:$EXPECTED_PORT" \
             "Traefik is not running. Run: bash $INSTALL_DIR/traefik-start.sh"
        ;;
    *)
        info "HTTP $HTTP_CODE — unexpected response, investigate manually"
        ;;
esac

# =============================================================================
# 13. .env KEY SETTINGS
# =============================================================================
hdr "13. .env Key Settings for $EXPECTED_HOST"

if [ -f "$INSTALL_DIR/.env" ]; then
    ALLOWED_HOSTS=$(grep "^ALLOWED_HOSTS=" "$INSTALL_DIR/.env" | cut -d= -f2-)
    CSRF_ORIGINS=$(grep "^CSRF_TRUSTED_ORIGINS=" "$INSTALL_DIR/.env" | cut -d= -f2-)
    NEXT_API_URL=$(grep "^NEXT_PUBLIC_API_URL=" "$INSTALL_DIR/.env" | cut -d= -f2-)

    info "ALLOWED_HOSTS       = $ALLOWED_HOSTS"
    info "CSRF_TRUSTED_ORIGINS= $CSRF_ORIGINS"
    info "NEXT_PUBLIC_API_URL = $NEXT_API_URL"

    if echo "$ALLOWED_HOSTS" | grep -q "$EXPECTED_HOST"; then
        ok "$EXPECTED_HOST in ALLOWED_HOSTS"
    else
        fail "$EXPECTED_HOST NOT in ALLOWED_HOSTS — Django will return 400 Bad Request" \
             "Edit $INSTALL_DIR/.env: add $EXPECTED_HOST to ALLOWED_HOSTS then: podman restart dalia20-web"
    fi

    if echo "$CSRF_ORIGINS" | grep -q "$EXPECTED_HOST"; then
        ok "$EXPECTED_HOST in CSRF_TRUSTED_ORIGINS"
    else
        warn "$EXPECTED_HOST not in CSRF_TRUSTED_ORIGINS — CSRF errors on POST requests" \
             "Add https://$EXPECTED_HOST to CSRF_TRUSTED_ORIGINS in $INSTALL_DIR/.env"
    fi

    if echo "$NEXT_API_URL" | grep -q "dalia"; then
        ok "NEXT_PUBLIC_API_URL is set: $NEXT_API_URL"
    else
        warn "NEXT_PUBLIC_API_URL may be wrong: $NEXT_API_URL" \
             "Set NEXT_PUBLIC_API_URL=https://$EXPECTED_HOST/api/dalia/v1 in $INSTALL_DIR/.env"
    fi
else
    fail ".env not found at $INSTALL_DIR/.env" \
         "Copy .env from private config overlay then update it for this VPS"
fi

# =============================================================================
# SUMMARY
# =============================================================================
echo ""
echo -e "${BOLD}${CYN}══════════════════════════════════════════════════════════════${RST}"
echo -e "${BOLD} SUMMARY${RST}"
echo -e "${BOLD}${CYN}══════════════════════════════════════════════════════════════${RST}"
echo -e "  ${GRN}PASS: $PASS${RST}   ${YLW}WARN: $WARN${RST}   ${RED}FAIL: $FAIL${RST}"
echo ""

if [ "${#FIXES[@]}" -gt 0 ]; then
    echo -e "${BOLD} FIX LIST (in order of priority):${RST}"
    echo ""
    N=0
    for fix in "${FIXES[@]}"; do
        N=$((N+1))
        SEVERITY=$(echo "$fix" | cut -d: -f1)
        MSG=$(echo "$fix" | cut -d: -f2-)
        if [ "$SEVERITY" = "FAIL" ]; then
            echo -e "  ${RED}[$N] FAIL${RST}$MSG"
        else
            echo -e "  ${YLW}[$N] WARN${RST}$MSG"
        fi
        echo ""
    done
else
    echo -e "  ${GRN}Everything looks good!${RST}"
fi

echo -e "${BOLD}${CYN}══════════════════════════════════════════════════════════════${RST}"
echo ""
echo " Quick reference — the most common fix for '$EXPECTED_HOST' not routing:"
echo ""
echo "  1. Edit $INSTALL_DIR/podman-compose.yml — find the nginx labels section:"
echo "     Change:  traefik.http.routers.dalia20-nginx.rule=HostRegexp(\`^dalia-.*\$\`)"
echo "         To:  traefik.http.routers.dalia20-nginx.rule=Host(\`$EXPECTED_HOST\`)"
echo ""
echo "  2. Restart nginx:"
echo "     cd $INSTALL_DIR && podman-compose up -d nginx"
echo ""
echo "  3. Edit $DYNAMIC_YML — update both maintenance rules:"
echo "     maintenance-router-specific: rule: \"Host(\`$EXPECTED_HOST\`) && Path(\`/maintenance.html\`)\""
echo "     maintenance-router-default:  rule: \"Host(\`$EXPECTED_HOST\`)\""
echo ""
echo "  4. Edit $INSTALL_DIR/.env — add $EXPECTED_HOST to:"
echo "     ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS, and update NEXT_PUBLIC_API_URL"
echo "     Then: podman restart dalia20-web"
echo ""
