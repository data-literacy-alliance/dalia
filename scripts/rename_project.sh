#!/bin/bash
set -e

# ICZ Project Rename Script
# Safely renames the ICZ starter template to your project name
# Usage: ./scripts/rename_project.sh <new-project-name>

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Check arguments
if [ $# -ne 1 ]; then
    echo "Usage: $0 <new-project-name>"
    echo ""
    echo "Example: $0 myproject"
    echo ""
    echo "This will:"
    echo "  - Rename database from 'icz' to 'myproject'"
    echo "  - Rename database user from 'icz' to 'myproject'"
    echo "  - Rename containers from 'django-generic-*' to 'myproject-*'"
    echo "  - Rename network from 'icz_icz-network' to 'myproject_myproject-network'"
    echo "  - Update all configuration files"
    echo "  - Rename directory from 'icz/' to 'myproject/'"
    exit 1
fi

NEW_NAME="$1"

# Validate project name (alphanumeric, lowercase, underscores/hyphens allowed)
if ! [[ "$NEW_NAME" =~ ^[a-z0-9_-]+$ ]]; then
    print_error "Project name must contain only lowercase letters, numbers, underscores, and hyphens"
fi

# Current values
OLD_NAME="icz"
OLD_DB_USER="icz"
OLD_DB_NAME="icz"
OLD_CONTAINER_PREFIX="django-generic"
OLD_NETWORK="icz_icz-network"

# New values
NEW_DB_USER="$NEW_NAME"
NEW_DB_NAME="$NEW_NAME"
NEW_CONTAINER_PREFIX="$NEW_NAME"
NEW_NETWORK="${NEW_NAME}_${NEW_NAME}-network"

# Get current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

print_info "Starting project rename from 'icz' to '$NEW_NAME'"
print_info "Project root: $PROJECT_ROOT"

# Confirmation
echo ""
read -p "This will modify files and recreate the database. Continue? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_error "Aborted by user"
fi

# Step 1: Stop containers
print_info "Stopping containers..."
cd "$PROJECT_ROOT"
make down || true

# Step 2: Create backups
print_info "Creating backups..."
BACKUP_DIR="$PROJECT_ROOT/backups/rename_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

cp .env.example "$BACKUP_DIR/.env.example.bak"
cp podman-compose.yml "$BACKUP_DIR/podman-compose.yml.bak"
cp podman-compose.tunnel.yml "$BACKUP_DIR/podman-compose.tunnel.yml.bak"
cp Makefile "$BACKUP_DIR/Makefile.bak"
cp pyproject.toml "$BACKUP_DIR/pyproject.toml.bak"
cp config/settings/base.py "$BACKUP_DIR/base.py.bak"
cp config/settings/production.py "$BACKUP_DIR/production.py.bak"
cp config/settings/testing.py "$BACKUP_DIR/testing.py.bak"

print_info "Backups created in: $BACKUP_DIR"

# Step 3: Update .env.example
print_info "Updating .env.example..."
sed -i "s/POSTGRES_DB=$OLD_DB_NAME/POSTGRES_DB=$NEW_DB_NAME/g" .env.example
sed -i "s/POSTGRES_USER=$OLD_DB_USER/POSTGRES_USER=$NEW_DB_USER/g" .env.example
sed -i "s|postgresql://$OLD_DB_USER:|postgresql://$NEW_DB_USER:|g" .env.example
sed -i "s|/$OLD_DB_NAME|/$NEW_DB_NAME|g" .env.example
sed -i "s/@$OLD_NAME\.local/@$NEW_NAME.local/g" .env.example

# Step 4: Update podman-compose.yml
print_info "Updating podman-compose.yml..."
sed -i "s/${OLD_NAME}-network/${NEW_NAME}-network/g" podman-compose.yml
sed -i "s/POSTGRES_DB:-$OLD_DB_NAME/POSTGRES_DB:-$NEW_DB_NAME/g" podman-compose.yml
sed -i "s/POSTGRES_USER:-$OLD_DB_USER/POSTGRES_USER:-$NEW_DB_USER/g" podman-compose.yml
sed -i "s|container_name: ${OLD_CONTAINER_PREFIX}-|container_name: ${NEW_CONTAINER_PREFIX}-|g" podman-compose.yml
sed -i "s|# \./ = $OLD_NAME/ directory|# ./ = $NEW_NAME/ directory|g" podman-compose.yml

# Step 5: Update podman-compose.tunnel.yml
print_info "Updating podman-compose.tunnel.yml..."
sed -i "s/${OLD_NAME}-network/${NEW_NAME}-network/g" podman-compose.tunnel.yml
sed -i "s/name: ${OLD_NAME}_${OLD_NAME}-network/name: ${NEW_NAME}_${NEW_NAME}-network/g" podman-compose.tunnel.yml
sed -i "s/container_name: ${OLD_NAME}-cloudflared/container_name: ${NEW_NAME}-cloudflared/g" podman-compose.tunnel.yml
sed -i "s/Joins the existing $OLD_NAME network/Joins the existing $NEW_NAME network/g" podman-compose.tunnel.yml

# Step 6: Update Makefile
print_info "Updating Makefile..."
sed -i "s/WEB_CONTAINER := ${OLD_CONTAINER_PREFIX}-web/WEB_CONTAINER := ${NEW_CONTAINER_PREFIX}-web/g" Makefile
sed -i "s/DB_CONTAINER := ${OLD_CONTAINER_PREFIX}-db/DB_CONTAINER := ${NEW_CONTAINER_PREFIX}-db/g" Makefile
sed -i "s/NGINX_CONTAINER := ${OLD_CONTAINER_PREFIX}-nginx/NGINX_CONTAINER := ${NEW_CONTAINER_PREFIX}-nginx/g" Makefile
sed -i "s/REDIS_CONTAINER := ${OLD_CONTAINER_PREFIX}-redis/REDIS_CONTAINER := ${NEW_CONTAINER_PREFIX}-redis/g" Makefile
sed -i "s/${OLD_NAME}-cloudflared/${NEW_NAME}-cloudflared/g" Makefile
sed -i "s/${OLD_NAME}_${OLD_NAME}-network/${NEW_NAME}_${NEW_NAME}-network/g" Makefile
sed -i "s/POSTGRES_DB:-$OLD_DB_NAME/POSTGRES_DB:-$NEW_DB_NAME/g" Makefile
sed -i "s/POSTGRES_USER:-$OLD_DB_USER/POSTGRES_USER:-$NEW_DB_USER/g" Makefile
sed -i "s|Run all commands from: $OLD_NAME/|Run all commands from: $NEW_NAME/|g" Makefile
sed -i "s|\"$OLD_NAME - Makefile|\"$NEW_NAME - Makefile|g" Makefile

# Step 7: Update pyproject.toml
print_info "Updating pyproject.toml..."
sed -i "s/name = \"$OLD_NAME\"/name = \"$NEW_NAME\"/g" pyproject.toml
sed -i "s/\"$OLD_NAME - Django 6.0/\"$NEW_NAME - Django 6.0/g" pyproject.toml

# Step 8: Update Django settings
print_info "Updating Django settings..."
sed -i "s/\"SITE_TITLE\": \"$OLD_NAME\"/\"SITE_TITLE\": \"$NEW_NAME\"/g" config/settings/base.py
sed -i "s/\"SITE_HEADER\": \"$OLD_NAME\"/\"SITE_HEADER\": \"$NEW_NAME\"/g" config/settings/base.py
sed -i "s/\"KEY_PREFIX\": \"$OLD_NAME\"/\"KEY_PREFIX\": \"$NEW_NAME\"/g" config/settings/base.py
sed -i "s/\"TITLE\": \"$OLD_NAME API\"/\"TITLE\": \"$NEW_NAME API\"/g" config/settings/base.py
sed -i "s/\"DESCRIPTION\": \"$OLD_NAME Django/\"DESCRIPTION\": \"$NEW_NAME Django/g" config/settings/base.py
sed -i "s/\"$OLD_NAME\"/\"$NEW_NAME\"/g" config/settings/production.py
sed -i "s/\"$OLD_NAME\"/\"$NEW_NAME\"/g" config/settings/testing.py

# Step 9: Update login template
print_info "Updating login template..."
sed -i "s/<title>Login - $OLD_NAME<\/title>/<title>Login - $NEW_NAME<\/title>/g" templates/registration/login.html
sed -i "s/<h1>$OLD_NAME<\/h1>/<h1>$NEW_NAME<\/h1>/g" templates/registration/login.html

# Step 10: Regenerate .env from updated .env.example
print_info "Regenerating .env file..."
cp .env.example .env

# Step 11: Remove old database data (fresh start)
print_info "Removing old database data..."
rm -rf data/postgres/*
rm -rf data/redis/*

# Step 12: Build containers with new names
print_info "Building containers with new names..."
make build

# Step 13: Start containers (will create new database)
print_info "Starting containers (creating fresh database)..."
make up

# Step 14: Wait for containers to be ready
print_info "Waiting for containers to start..."
sleep 10

# Step 15: Verify containers are running
print_info "Verifying containers..."
if podman ps | grep -q "${NEW_CONTAINER_PREFIX}-web"; then
    print_info "✓ Web container running"
else
    print_error "Web container not running"
fi

if podman ps | grep -q "${NEW_CONTAINER_PREFIX}-db"; then
    print_info "✓ Database container running"
else
    print_error "Database container not running"
fi

if podman ps | grep -q "${NEW_CONTAINER_PREFIX}-nginx"; then
    print_info "✓ Nginx container running"
else
    print_error "Nginx container not running"
fi

if podman ps | grep -q "${NEW_CONTAINER_PREFIX}-redis"; then
    print_info "✓ Redis container running"
else
    print_error "Redis container not running"
fi

# Success message
echo ""
print_info "========================================="
print_info "Project renamed successfully!"
print_info "========================================="
echo ""
echo "Old name: $OLD_NAME"
echo "New name: $NEW_NAME"
echo ""
echo "Changes made:"
echo "  - Database name: $OLD_DB_NAME → $NEW_DB_NAME"
echo "  - Database user: $OLD_DB_USER → $NEW_DB_USER"
echo "  - Container prefix: $OLD_CONTAINER_PREFIX → $NEW_CONTAINER_PREFIX"
echo "  - Network: $OLD_NETWORK → $NEW_NETWORK"
echo ""
echo "Backups saved to: $BACKUP_DIR"
echo ""
echo "Next steps:"
echo "  1. Test admin login: http://localhost:7080/admin/"
echo "  2. Verify health check: http://localhost:7080/api/v1/health/"
echo "  3. Check logs: make logs"
echo "  4. Rename directory: cd .. && mv icz $NEW_NAME && cd $NEW_NAME"
echo ""
print_warn "NOTE: You need to manually rename the directory from 'icz/' to '$NEW_NAME/'"
print_warn "      Run: cd /home/mzubilewicz/django_generic && mv icz $NEW_NAME"
echo ""
