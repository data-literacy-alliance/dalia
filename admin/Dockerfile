# maintenance/Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY admin/app /app/app
# COPY scripts /scripts

# Install system packages (curl + ip command)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    iproute2 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir fastapi uvicorn requests

EXPOSE 80
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]