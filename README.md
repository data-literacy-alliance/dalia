# Dalia 2.0

NFDI Open Educational Resources portal — Django 6.0 + Next.js 14

## Overview

Dalia is an open educational resources (OER) portal built for the NFDI (Nationale Forschungsdateninfrastruktur) community. It provides curation, discovery, and access to learning resources across research communities. Users authenticate via the NFDI AAI identity federation (IAM4NFDI), enabling single sign-on across NFDI services. The backend is a Django REST API with a rich unfold-based admin interface; the frontend is a server-rendered Next.js application.

The stack is fully containerised and deployed using rootless Podman with a Traefik reverse proxy for multi-environment routing (dev / staging / prod).

## Architecture

```
                         ┌──────────────────────────────┐
                         │         Traefik (proxy)       │
                         │         traefik-compose.yml   │
                         └────────────┬─────────────────┘
                                      │
             ┌────────────────────────┼───────────────────┐
             │                        │                   │
      ┌──────▼──────┐       ┌─────────▼──────┐   ┌──────▼──────┐
      │  nginx      │       │  Django (web)  │   │  Next.js    │
      │  static +   │       │  gunicorn      │   │  frontend   │
      │  media      │       │  port 8000     │   │  port 3000  │
      └─────────────┘       └───┬─────┬──────┘   └─────────────┘
                                │     │
              ┌─────────────────┘     └──────────────────────┐
              │                                               │
      ┌───────▼──────┐  ┌───────────────┐  ┌────────────────▼──┐
      │ PostgreSQL   │  │  Redis        │  │  Elasticsearch    │
      │  (primary    │  │  cache +      │  │  (search index)   │
      │   datastore) │  │  sessions)    │  │                   │
      └──────────────┘  └───────────────┘  └───────────────────┘
                                │
                      ┌─────────▼──────┐
                      │  Apache Fuseki │
                      │  (SPARQL)      │
                      └────────────────┘
```

Authentication: NFDI AAI (IAM4NFDI) via OpenID Connect — handled by django-allauth with a custom adapter (`apps/nfdi_auth/`).

## Stack

- **Backend:** Django 6.0, Django REST Framework, django-unfold admin, django-allauth + nfdi_auth
- **Frontend:** Next.js 14 (App Router), React, pnpm
- **Databases:** PostgreSQL 16 (system of record), Apache Jena Fuseki (SPARQL/RDF), Elasticsearch 8.17 (search)
- **Cache / sessions:** Redis 7
- **Orchestration:** Rootless Podman + podman-compose, Traefik reverse proxy
- **Auth:** NFDI AAI (IAM4NFDI) via OpenID Connect

## Repository layout

```
.
├── apps/               # Django applications
│   ├── core/           # Base models, permissions, health checks
│   ├── curation/       # Resource curation (Resource, ResourceContent, M2M)
│   ├── nfdi_auth/      # NFDI AAI OIDC adapter and allauth integration
│   └── users/          # Custom user model
├── config/             # Django settings package (base / production / testing)
├── content/            # Static content (privacy policy, pages)
├── docker/             # Container support files and entrypoints
├── frontend/           # Next.js 14 application
│   ├── app/            # App Router pages and layouts
│   ├── components/     # Shared React components
│   └── lib/            # Utility modules and constants
├── maintenance/        # Maintenance mode HTML + nginx config
├── scripts/            # Operational shell scripts
├── static/             # Django static files
├── templates/          # Django HTML templates
├── traefik/            # Traefik configuration (dynamic.yml, .env)
├── Makefile            # All project commands
├── podman-compose.yml  # Application service definitions
├── traefik-compose.yml # Traefik + admin/maintenance service definitions
└── traefik-start.sh    # Start Traefik stack
```

## Quickstart

Prerequisites: rootless Podman, podman-compose, GNU Make.

```bash
cp .env.example .env        # fill in NFDI client ID/secret, DB password, etc.
make build-web              # build Django container
make build-frontend         # build Next.js container
make up                     # start all containers
```

The admin panel is at `http://localhost/admin/`. The frontend is at `http://localhost/`.

To create an initial superuser:

```bash
make createsuperuser
```

## Make targets

All commands run from the project root (where `Makefile` lives). Container operations are executed inside the containers — never on the host directly.

### Setup

| Target | Description |
|---|---|
| `init-env` | Regenerate .env from .env.example (overwrites existing) |
| `rename-project` | Rename project from ICZ to your project name (Usage: `make rename-project NAME=myproject`) |

### Containers

| Target | Description |
|---|---|
| `build` | Build all containers (no cache) |
| `build-web` | Rebuild only the web (Django) container |
| `build-frontend` | Rebuild only the frontend (Next.js) container |
| `build-fuseki` | Rebuild only the Fuseki container |
| `regenerate-lockfile` | Regenerate frontend pnpm-lock.yaml (run after adding/removing packages) |
| `up` | Start all containers (detached) |
| `up-all` | Start Traefik + all dalia20 containers (use for manual full startup) |
| `down` | Stop and remove all containers |
| `restart` | Restart all containers |
| `logs` | View logs (all containers, follow) |

### Django

| Target | Description |
|---|---|
| `shell` | Django shell (interactive) |
| `dbshell` | PostgreSQL shell (interactive) |
| `bash` | Bash shell in web container |
| `migrate` | Run database migrations |
| `makemigrations` | Create new migrations (works whether web container is running or not) |
| `check-migrations` | Verify no migration files are missing |
| `list-migrations` | List migration files (rootless Podman) |
| `createsuperuser` | Create Django superuser |
| `collectstatic` | Collect static files (clears stale files first) |
| `check` | Run Django system checks |
| `convert-privacy-policy` | Convert privacy policy DOCX to Markdown |

### Frontend

| Target | Description |
|---|---|
| `regenerate-lockfile` | Regenerate frontend pnpm-lock.yaml after adding/removing packages |

### Database

| Target | Description |
|---|---|
| `backup-db` | Backup PostgreSQL database (includes DROP statements for safe restore) |
| `dbrestore` | Restore database from backup (use `BACKUP=path/to/file.sql`) |
| `reset-db` | Wipe database and restart fresh (DEV ONLY — destroys all data) |
| `es-setup` | Fix Elasticsearch data directory ownership (run once on first setup) |

### Cache

| Target | Description |
|---|---|
| `redis-cli` | Open Redis CLI |
| `flush-cache` | Flush Redis cache |

### Testing & quality

| Target | Description |
|---|---|
| `test` | Run tests (checks migrations first) |
| `test-cov` | Run tests with coverage report |
| `lint` | Run code quality checks (ruff) |
| `format` | Format code (ruff) |

### Utilities

| Target | Description |
|---|---|
| `git-add` | Stage all changes including container-created files (rootless Podman) |
| `git-commit` | Commit staged changes (rootless Podman, use `MSG="message"`) |
| `deploy` | Deploy to production (rebuild and restart containers) |
| `rollback` | Rollback last deployment |
| `clean` | Clean temporary files (runs on host) |

### Autostart

| Target | Description |
|---|---|
| `autostart-enable` | Register @reboot cron job (30s delay, starts Traefik + dalia20) |
| `autostart-disable` | Remove @reboot cron job |
| `autostart-status` | Show whether @reboot autostart is configured |
| `autostart-update` | Update autostart path (run after moving or renaming the project folder) |

## Configuration

All configuration via environment variables. Copy `.env.example` to `.env` and fill in the values.

Key variables:

| Variable | Description |
|---|---|
| `SECRET_KEY` | Django secret key (50 chars, random) |
| `DATABASE_URL` | PostgreSQL connection string |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | PostgreSQL credentials |
| `REDIS_URL` | Redis connection string |
| `IAM4NFDI_CLIENT_ID`, `IAM4NFDI_CLIENT_SECRET` | NFDI AAI OIDC credentials |
| `ALLOWED_HOSTS` | Comma-separated hostnames |
| `CORS_ALLOWED_ORIGINS` | Comma-separated list of origins permitted by CORS (e.g. `https://your-frontend.example.com`). Must be set when the frontend is served from a different host than the backend. |
| `DEV_FRONTEND_URL`, `STAGING_FRONTEND_URL` | Frontend redirect targets after login (dev/staging environments) |
| `ELASTICSEARCH_HOST` | Elasticsearch endpoint |
| `DALIA_TRIPLESTORE_BASE_URL` | Internal Fuseki endpoint |
| `NEXT_PUBLIC_MATOMO_URL`, `NEXT_PUBLIC_MATOMO_CONTAINER_ID` | Matomo analytics (both must be set or neither) |
| `DEBUG` | Set to `True` for development (never in production) |
| `GUNICORN_WORKERS`, `GUNICORN_TIMEOUT` | Gunicorn tuning |

See `.env.example` for the full list with comments.

## Development workflow

Edit files on the host with your IDE. The source tree is bind-mounted into the containers (`.:/app:z`) and gunicorn runs with `--reload`, so code changes are picked up automatically without rebuilding.

### Rootless Podman and file ownership

Rootless Podman uses sub-UID namespace mapping. Files created inside the container (migrations, media uploads, log files) appear on the host owned by a sub-UID — not your login user. This affects git operations on those files.

- `git add` works directly for source files you create on the host.
- For container-created files (migrations, etc.), use `podman unshare`:

```bash
# Stage migration files created inside the container
podman unshare git add apps/myapp/migrations/0002_auto.py
git commit -m "Add migration"

# Or use the make shortcuts
make git-add
make git-commit MSG="Add migration"
```

Never use `chown` on container-created files — it breaks the container's write access.

### Elasticsearch setup

On first start or after `make down`, fix the data directory ownership:

```bash
make es-setup
make up
```

## Testing

```bash
make test          # pytest in container (migration check runs first)
make test-cov      # coverage report (htmlcov/)
make lint          # ruff linter
make format        # ruff formatter
```

Tests use `config.settings.testing` (SQLite in-memory, no external services).

## Deployment

Production runs using rootless Podman and systemd. The `traefik-compose.yml` and `traefik-start.sh` / `traefik-stop.sh` scripts orchestrate the Traefik reverse proxy.

Place the production `.env` at `traefik/.env` (the path can be overridden via the `TRAEFIK_ENV_PATH` environment variable passed to `host-trigger.py`).

For autostart on server reboot:

```bash
make autostart-enable
make autostart-status
```

Logs are available via `make logs` or `journalctl` for the systemd unit.

## License

MIT — see [LICENSE](LICENSE).

## Contributing

Open an issue or pull request. Code style: ruff for Python (`make lint` / `make format`), Prettier/ESLint for TypeScript. Tests are required for new business logic and bug fixes.
