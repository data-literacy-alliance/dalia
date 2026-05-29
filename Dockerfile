# ============================================================
# Stage 1: Builder (Install dependencies in venv)
# ============================================================
FROM python:3.13-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment at /opt/venv
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy dependency specification
COPY pyproject.toml ./

# Install pip-tools and compile requirements from pyproject.toml
RUN pip install --no-cache-dir pip-tools && \
    pip-compile pyproject.toml --output-file=requirements.txt --resolver=backtracking && \
    pip-compile pyproject.toml --extra=dev --output-file=requirements-dev.txt --resolver=backtracking

# Install all dependencies (production + dev) into venv
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r requirements-dev.txt

# ============================================================
# Stage 2: Runtime (Copy venv, minimal image)
# ============================================================
FROM python:3.13-slim

# Create non-root user
RUN groupadd -r worktrack && useradd -r -g worktrack -d /app -s /sbin/nologin worktrack

WORKDIR /app

# Install runtime dependencies only (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    postgresql-client \
    pandoc \
    && rm -rf /var/lib/apt/lists/*

# Copy venv from builder (industry gold standard)
COPY --from=builder /opt/venv /opt/venv

# Update PATH to include venv and PYTHONPATH to include apps/
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app/apps:$PYTHONPATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Copy entrypoint script
COPY docker/entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh

# Copy application code
COPY --chown=worktrack:worktrack . .

# Create directories for bind mounts (may be overridden by volumes)
RUN mkdir -p /app/static /app/media /app/logs && \
    chown -R worktrack:worktrack /app

# Switch to non-root user
USER worktrack

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health/ || exit 1

# Production entrypoint and default command
ENTRYPOINT ["entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60", "--reload", "--access-logfile", "-", "--error-logfile", "-"]
