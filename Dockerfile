# ==============================
# Dockerfile — Unraid Torrent Helper (frontend + backend)
# ==============================

########## 1) FRONTEND BUILD ##########
FROM node:20-alpine AS webbuild
WORKDIR /ui

# Copy frontend sources
# (assumes your project structure has /frontend and /backend folders)
COPY frontend/package.json frontend/package-lock.json* ./ 
RUN npm ci

COPY frontend/ ./
RUN npm run build

########## 2) BACKEND RUNTIME ##########
FROM python:3.11-slim AS app
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System deps (rsync for migrations, curl for healthcheck)
RUN apt-get update && \
    apt-get install -y --no-install-recommends rsync curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy backend requirements early to leverage Docker layer cache
COPY backend/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

# Copy backend source
COPY backend/ ./

# Copy built frontend into FastAPI static dir
# Make sure your backend mounts StaticFiles at / (we did in previous parts)
# This will serve the SPA.
RUN mkdir -p /app/app/static
COPY --from=webbuild /ui/dist/ /app/app/static/

# Defaults (override via docker-compose or Unraid template)
ENV QB_URL=http://192.168.1.118:8080 \
    QB_USERNAME=admin \
    QB_PASSWORD=admin \
    APP_ADMIN_USER=admin \
    APP_ADMIN_PASS=admin \
    APP_DATA_DIR=/config \
    APP_MAPPINGS='[{"container":"/data","host":"/mnt/user/torrents"},{"container":"/data/torrents","host":"/mnt/user/media/torrents"}]' \
    APP_RSYNC_FLAGS="-aHAX --info=progress2 --partial --inplace --numeric-ids --preallocate" \
    APP_MAX_CONCURRENT=2

# Persisted app data (logs, sqlite, etc.)
VOLUME ["/config"]

EXPOSE 8088

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD curl -fsS http://localhost:8088/api/healthz || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8088"]