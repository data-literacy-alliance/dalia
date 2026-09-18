.PHONY: help build build-frontend build-web build-fuseki up down restart logs shell dbshell bash migrate makemigrations \
        createsuperuser test test-cov lint format check collectstatic clean backup-db \
        check-migrations git-add git-commit list-migrations init-env \
        dbrestore deploy rollback up-tunnel down-tunnel redis-cli flush-cache rename-project setup-private push-private \
        reset-db up-all autostart-status autostart-enable autostart-disable autostart-update \
        convert-privacy-policy regenerate-lockfile

# Default target
.DEFAULT_GOAL := help

# Autostart cron marker — identifies our @reboot entry in crontab
AUTOSTART_MARKER := dalia20-autostart

# Container names
WEB_CONTAINER := dalia20-web
DB_CONTAINER := dalia20-db
NGINX_CONTAINER := dalia20-nginx
REDIS_CONTAINER := dalia20-redis

# CI-friendly: detect if running in terminal
TTY := $(shell test -t 0 && echo "-it" || echo "-i")

help: ## Show this help message
	@echo "ICZ - Makefile Commands"
	@echo ""
	@echo "Run all commands from: dalia20/ directory"
	@echo ""
	@echo "Container Management:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ============================================================
# Environment Setup
# ============================================================

init-env: ## Regenerate .env from .env.example (overwrites existing)
	@echo "Generating .env from .env.example..."
	@cp .env.example .env
	@echo ".env regenerated from .env.example"

# ============================================================
# Autostart (crontab @reboot)
# ============================================================

autostart-status: ## Show whether @reboot autostart is configured
	@echo "=== Autostart status ==="
	@crontab -l 2>/dev/null | grep -F "$(AUTOSTART_MARKER)" \
		&& echo "Status: ENABLED" \
		|| echo "Status: DISABLED"

autostart-enable: ## Register @reboot cron job (30s delay, starts Traefik + dalia20)
	@chmod +x $(CURDIR)/scripts/on-reboot.sh
	@if crontab -l 2>/dev/null | grep -qF "$(AUTOSTART_MARKER)"; then \
		echo "Already ENABLED. Run 'make autostart-update' to refresh the path."; \
	else \
		( crontab -l 2>/dev/null; echo "@reboot sleep 30 && $(CURDIR)/scripts/on-reboot.sh >> /tmp/dalia20-reboot.log 2>&1 # $(AUTOSTART_MARKER)" ) | crontab -; \
		echo "Autostart ENABLED."; \
		echo "Entry: @reboot sleep 30 && $(CURDIR)/scripts/on-reboot.sh"; \
		echo "Logs:  /tmp/dalia20-reboot.log"; \
	fi

autostart-disable: ## Remove @reboot cron job
	@if crontab -l 2>/dev/null | grep -qF "$(AUTOSTART_MARKER)"; then \
		crontab -l 2>/dev/null | grep -vF "$(AUTOSTART_MARKER)" | crontab -; \
		echo "Autostart DISABLED."; \
	else \
		echo "Nothing to remove — autostart was not enabled."; \
	fi

autostart-update: ## Update autostart path (run after moving or renaming the project folder)
	@$(MAKE) autostart-disable
	@$(MAKE) autostart-enable

# ============================================================
# Container Management
# ============================================================

up-all: ## Start Traefik + all dalia20 containers (use for manual full startup)
	@echo "Starting Traefik..."
	@bash $(CURDIR)/traefik-start.sh
	@echo "Starting dalia20 containers..."
	@$(MAKE) up

build: init-env ## Build all containers (no cache)
	$(MAKE) format
	podman-compose build --no-cache

build-frontend: init-env ## Rebuild only the frontend (Next.js) container
	podman-compose build --no-cache frontend

build-web: init-env ## Rebuild only the web (Django) container
	$(MAKE) format
	podman-compose build --no-cache web

build-fuseki: init-env ## Rebuild only the Fuseki container
	podman-compose build --no-cache fuseki

regenerate-lockfile: ## Regenerate frontend pnpm-lock.yaml (run after adding/removing packages)
	podman run --rm \
		-v $(CURDIR)/frontend:/app:z \
		-w /app \
		docker.io/library/node:22-alpine \
		sh -c "npm install -g pnpm@latest --silent 2>/dev/null && pnpm install --ignore-scripts 2>&1 | tail -5"

up: init-env ## Start all containers (detached)
	podman-compose up -d
	@echo "Containers started. Access at http://localhost:8000"

down: ## Stop and remove all containers
	podman-compose down

up-tunnel: init-env ## Start all containers including Cloudflare tunnel (requires CF_TUNNEL_TOKEN in .env)
	@test -f .env || (echo "ERROR: .env not found. Run 'make up' first or copy .env.example"; exit 1)
	@CF_TOKEN=$$(grep -s '^CF_TUNNEL_TOKEN=' .env | cut -d= -f2 | tr -d '[:space:]'); \
	if [ -z "$$CF_TOKEN" ]; then \
		echo "ERROR: CF_TUNNEL_TOKEN not set in .env"; \
		echo "Add: CF_TUNNEL_TOKEN=your-token"; \
		exit 1; \
	fi; \
	podman-compose up -d; \
	podman rm -f dalia20-cloudflared 2>/dev/null || true; \
	podman run -d \
		--name dalia20-cloudflared \
		--network icz_django-generic-network \
		--restart unless-stopped \
		docker.io/cloudflare/cloudflared:latest \
		tunnel --no-autoupdate run --token "$$CF_TOKEN"
	@echo "All containers started including Cloudflare tunnel"

down-tunnel: ## Stop all containers including Cloudflare tunnel
	-podman stop dalia20-cloudflared 2>/dev/null; podman rm dalia20-cloudflared 2>/dev/null
	podman-compose down

restart: ## Restart all containers
	podman-compose restart

logs: ## View logs (all containers, follow)
	podman-compose logs -f

# ============================================================
# Django Commands (ALL execute inside container)
# ============================================================

shell: ## Django shell (interactive)
	podman exec -it $(WEB_CONTAINER) python manage.py shell

dbshell: ## PostgreSQL shell (interactive)
	podman exec -it $(WEB_CONTAINER) python manage.py dbshell

bash: ## Bash shell in web container
	podman exec -it $(WEB_CONTAINER) bash

migrate: ## Run database migrations
	podman exec $(TTY) $(WEB_CONTAINER) python manage.py migrate

makemigrations: ## Create new migrations (works whether web container is running or not)
	podman-compose run --rm web python manage.py makemigrations --noinput
	@echo ""
	@echo "Migration files created in apps/*/migrations/ (bind-mounted, persists on host)."
	@echo "Use 'make git-add' or 'podman unshare bash' for git operations on migration files."

createsuperuser: ## Create Django superuser
	podman exec -it $(WEB_CONTAINER) python manage.py createsuperuser

collectstatic: ## Collect static files (clears stale files first)
	podman exec $(TTY) $(WEB_CONTAINER) python manage.py collectstatic --clear --noinput

check: ## Run Django system checks
	podman exec $(TTY) $(WEB_CONTAINER) python manage.py check

# ============================================================
# Migration Management
# ============================================================

check-migrations: ## Verify no migration files are missing
	@podman exec $(TTY) $(WEB_CONTAINER) python manage.py makemigrations --check --dry-run

list-migrations: ## List migration files (rootless Podman)
	podman unshare ls -la apps/*/migrations/

# ============================================================
# Testing & Quality (ALL execute inside container)
# ============================================================

test: check-migrations ## Run tests (checks migrations first)
	podman exec $(TTY) $(WEB_CONTAINER) pytest

test-cov: ## Run tests with coverage report
	podman exec $(TTY) $(WEB_CONTAINER) pytest --cov=apps --cov-report=term-missing --cov-report=html

lint: ## Run code quality checks (ruff)
	podman exec $(TTY) $(WEB_CONTAINER) ruff check --no-cache apps/ config/

format: ## Format code (ruff)
	podman exec $(TTY) $(WEB_CONTAINER) ruff format --no-cache apps/ config/

# ============================================================
# Host File Operations (rootless Podman user namespace)
# ============================================================
# Files created by the container are owned by the container's mapped sub-UID.
# Use 'podman unshare' to access them from the host without changing ownership.
# NEVER chown container files -- it breaks the container's write access.

git-add: ## Stage all changes including container-created files (rootless Podman)
	podman unshare git add -A

git-commit: ## Commit staged changes (rootless Podman, use MSG="message")
	podman unshare git commit -m "$(MSG)"

# ============================================================
# Elasticsearch Utilities
# ============================================================

es-setup: ## Fix Elasticsearch data directory ownership (run once on first setup or after make down)
	@echo "Setting Elasticsearch data directory ownership to container UID 1000..."
	podman unshare chown -R 1000:0 $(CURDIR)/data/elasticsearch
	@echo "Done. Run 'make up' to start Elasticsearch."

# ============================================================
# Database Utilities
# ============================================================

reset-db: ## Wipe database and restart fresh (DEV ONLY — destroys all data)
	@echo "Stopping containers..."
	podman-compose down
	@echo "Wiping postgres data (rootless Podman user namespace)..."
	podman unshare bash -c "rm -rf $(CURDIR)/data/postgres/* $(CURDIR)/data/postgres/.[!.]*"
	@echo "Starting containers with fresh database..."
	podman-compose up -d
	@echo "Waiting 20s for DB init and migrations..."
	@sleep 20
	@podman logs $(WEB_CONTAINER) 2>&1 | grep -E "Applying|Superuser|Starting|Error|Traceback" | tail -20
	@echo "Done. Fresh database ready."

backup-db: ## Backup PostgreSQL database (safe restore: includes DROP statements)
	mkdir -p backups
	podman exec $(DB_CONTAINER) pg_dump --clean --if-exists -U $${POSTGRES_USER:-dalia20} $${POSTGRES_DB:-dalia20} > backups/backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "Backup saved to backups/"

dbrestore: ## Restore database from backup (use BACKUP=path/to/file.sql)
	@if [ -z "$(BACKUP)" ]; then \
		echo "Error: BACKUP variable required. Usage: make dbrestore BACKUP=backups/backup_20260215_120000.sql"; \
		exit 1; \
	fi
	cat $(BACKUP) | podman exec -i $(DB_CONTAINER) psql -U $${POSTGRES_USER:-dalia20} -v ON_ERROR_STOP=1 $${POSTGRES_DB:-dalia20}
	@echo "Database restored from $(BACKUP)"

# ============================================================
# Redis Utilities
# ============================================================

.PHONY: redis-cli
redis-cli: ## Open Redis CLI
	podman exec -it $(REDIS_CONTAINER) redis-cli

.PHONY: flush-cache
flush-cache: ## Flush Redis cache
	podman exec $(REDIS_CONTAINER) redis-cli FLUSHDB
	@echo "Redis cache flushed"

# ============================================================
# Deployment
# ============================================================

deploy: ## Deploy to production (rebuild and restart containers)
	@echo "Deploying to production..."
	podman-compose build --no-cache
	podman-compose down
	podman-compose up -d
	@echo "Deployment complete. Containers restarted with latest code."

rollback: ## Rollback last deployment
	@echo "Rollback target not yet implemented. Manual intervention required."
	@echo "Steps: 1) git checkout <previous-commit> 2) make dbrestore BACKUP=<backup-file> 3) make deploy"

# ============================================================
# Content Management
# ============================================================

convert-privacy-policy: ## Convert privacy policy DOCX → Markdown (uses pandoc/core container)
	@bash $(CURDIR)/scripts/convert-privacy-policy.sh

# ============================================================
# Cleanup
# ============================================================

clean: ## Clean temporary files (runs on host)
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf htmlcov/ .coverage .pytest_cache/

# ============================================================
# Project Customization
# ============================================================

# ============================================================
# Private config overlay (for trusted developers / new VPS)
# ============================================================
# Store the private repo URL once in .syncrc (gitignored):
#   echo "PRIVATE_REPO=https://github.com/data-literacy-alliance/dalia-private-config.git" > .syncrc
-include .syncrc
PRIVATE_REPO ?=
PRIVATE_TMP  := /tmp/dalia-private-config

.PHONY: setup-private push-private

setup-private: ## Restore private config overlay into this directory (run once per new checkout)
	@[ -n "$(PRIVATE_REPO)" ] || { \
		echo "Set PRIVATE_REPO in .syncrc:"; \
		echo "  echo 'PRIVATE_REPO=https://github.com/data-literacy-alliance/dalia-private-config.git' > .syncrc"; \
		exit 1; \
	}
	rm -rf $(PRIVATE_TMP)
	git clone --depth 1 $(PRIVATE_REPO) $(PRIVATE_TMP)
	rsync -a $(PRIVATE_TMP)/overlay/ $(CURDIR)/
	rm -rf $(PRIVATE_TMP)
	@echo "Private config restored."

push-private: ## Backup sensitive files to private config repo
	@[ -n "$(PRIVATE_REPO)" ] || { \
		echo "Set PRIVATE_REPO in .syncrc:"; \
		echo "  echo 'PRIVATE_REPO=https://github.com/data-literacy-alliance/dalia-private-config.git' > .syncrc"; \
		exit 1; \
	}
	rm -rf $(PRIVATE_TMP)
	git clone --depth 1 $(PRIVATE_REPO) $(PRIVATE_TMP)
	mkdir -p $(PRIVATE_TMP)/overlay/traefik
	rsync -a $(CURDIR)/.env     $(PRIVATE_TMP)/overlay/
	rsync -a $(CURDIR)/hosts    $(PRIVATE_TMP)/overlay/
	rsync -a $(CURDIR)/traefik/ $(PRIVATE_TMP)/overlay/traefik/
	@[ -f $(CURDIR)/podman-compose.tunnel.yml ] && \
		rsync -a $(CURDIR)/podman-compose.tunnel.yml $(PRIVATE_TMP)/overlay/ || true
	cd $(PRIVATE_TMP) && git add -A && \
		( git diff --cached --quiet \
			&& echo "  Private config unchanged." \
			|| git commit -m "update: $$(date '+%Y-%m-%d %H:%M')" ) && \
		git push
	rm -rf $(PRIVATE_TMP)
	@echo "Private config pushed."

# ============================================================
# Project Customization
# ============================================================

rename-project: ## Rename project from ICZ to your project name (Usage: make rename-project NAME=myproject)
	@if [ -z "$(NAME)" ]; then \
		echo "Error: NAME parameter required"; \
		echo "Usage: make rename-project NAME=myproject"; \
		exit 1; \
	fi
	@./scripts/rename_project.sh $(NAME)
