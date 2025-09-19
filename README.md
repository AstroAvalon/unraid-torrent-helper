# Unraid Torrent Helper

Small web app (FastAPI + React) to:
- Detect **misplaced** qBittorrent torrents (save path under `/data/...` instead of `/data/torrents/...`)
- **Migrate** data with `rsync` (preserve hardlinks/attrs), update save path, and recheck
- **Fix "Downloading metadata"** torrents (reannounce / DHT nudge / replace `.torrent` from backups)
- Stream **live progress** via SSE

Works great with Unraid 6.12.x and qBittorrent (binhex or official) in Docker.

---

## Features

- Dashboard (name, hash, size, state, progress, save path, misplaced?, suggested target)
- Tabs with **counts**: Misplaced · OK · Stuck
- **Search** + **Sort** on any column
- **Bulk migrate** (supports Dry-Run; optional delete old)
- **Right-side live log** that stays visible while scrolling
- Robust **path mapping** (container↔host) with longest-prefix rule
- **Resilient SSE** with heartbeats and auto-reconnect
- Minimal local auth (username/password; ready to sit behind SWAG/Traefik)

---

## Quick Start (Docker Compose)

```bash
git clone <your-repo> unraid-torrent-helper
cd unraid-torrent-helper
docker compose up -d --build
# open http://localhost:8088  (user: admin / pass: change-me)
```

The compose file:
- Builds the frontend and backend into a **single image**
- Mounts Unraid shares to **identical paths** inside the container (`/mnt/user/...`)
- Exposes port **8088**

---

## Unraid Deployment

### Option A: Import template
Use `unraid-template.xml` (Community Apps format). It defines:
- Port 8088
- Identity bind mounts for `/mnt/user/torrents`, `/mnt/user/media/torrents`, `/mnt/user/media/reseeds`, `/mnt/user/media/backup`
- Env vars for qB Web API and app config

### Option B: Manually add container
In Unraid **Docker** tab → **Add Container**:
- **Repository**: your built image (or build via compose locally and push)
- **Network**: Bridge (or your preferred)
- **Port**: 8088 → 8088
- **Volumes** (identity binds; paths inside the container must match the host):
  - `/mnt/user/torrents` → `/mnt/user/torrents`
  - `/mnt/user/media/torrents` → `/mnt/user/media/torrents`
  - `/mnt/user/media/reseeds` → `/mnt/user/media/reseeds` (optional)
  - `/mnt/user/media/backup` → `/mnt/user/media/backup` (optional for .torrent backups)
  - `/mnt/user/appdata/unraid-torrent-helper` → `/config`
- **Environment**:
  - `QB_URL=http://<qb-ip>:<qb-port>` (e.g. `http://192.168.1.118:8080`)
  - `QB_USERNAME=<your-qb-user>`
  - `QB_PASSWORD=<your-qb-pass>`
  - `APP_ADMIN_USER=admin`
  - `APP_ADMIN_PASS=<set-a-strong-password>`
  - `APP_DATA_DIR=/config`
  - `APP_MAPPINGS=[{"container":"/data","host":"/mnt/user/torrents"},{"container":"/data/torrents","host":"/mnt/user/media/torrents"},{"container":"/reseeds","host":"/mnt/user/media/reseeds"}]`
  - `APP_RSYNC_FLAGS=-aHAX --info=progress2 --partial --inplace --numeric-ids --preallocate`
  - `APP_MAX_CONCURRENT=2`
- **User**: `99:100` (nobody:users) is typical on Unraid
- **Restart policy**: unless-stopped

Open the WebUI: `http://SERVER-IP:8088`.

---

## Path Mapping (very important)

`APP_MAPPINGS` tells the helper how to translate **qBittorrent’s container paths** → **host paths inside this container**:

```json
[
  { "container": "/data",          "host": "/mnt/user/torrents" },
  { "container": "/data/torrents", "host": "/mnt/user/media/torrents" },
  { "container": "/reseeds",       "host": "/mnt/user/media/reseeds" }
]
```

- “Container” values must match how qBittorrent sees paths (inside qB’s container).
- “Host” values must be real paths **inside the helper container**. Easiest: identity bind your Unraid shares to the same `/mnt/user/...` path.

Check what the app sees:
```
GET http://<helper-host>:8088/api/config
```

---

## UI Basics

- **Dry Run** toggle (top right): plan-only, no file writes; still shows rsync command and plan.
- Tabs show **counts**; **OK tab hides migrate** actions.
- **Search** (name/hash) and **click headers** to sort (asc/desc).
- **Side Log** shows live `state` and `progress` events (SSE).
- When migrating:
  - Dry run shows:
    - mapping (`/data/...` → `/mnt/user/...`)
    - full rsync command preview (`rsync --dry-run ...`)
    - plan summary
    - “dry-run complete”
  - Real run:
    - pauses torrent,
    - runs rsync (progress lines stream),
    - sets new location (`/data/torrents/...`),
    - rechecks and resumes.

---

## Backend Endpoints (for testing)

- `GET /api/healthz` → `200 OK` when app is up
- `GET /api/config` → active config (including parsed mappings)
- `GET /api/torrents` → list + misplaced classification + suggested target
- `POST /api/actions/migrate`
  ```json
  { "hashes": ["<infohash1>", "<infohash2>"], "delete_old": false }
  ```
  (Dry-run is controlled by the UI toggle / config)
- `POST /api/actions/fix-metadata`
  ```json
  { "hashes": ["<infohash>"] }
  ```
- `GET /api/events/stream` → SSE stream (open in the browser to see raw events)

---

## Rsync Strategy

Default flags (override with `APP_RSYNC_FLAGS`):
```
-aHAX --info=progress2 --partial --inplace --numeric-ids --preallocate
```
- `-aHAX`: archive + preserve hardlinks, ACLs, xattrs
- `--inplace`: safer with large files/hardlinks; disable if you prefer temp files
- **Dry run** auto-injects `--dry-run`.

**Delete old:** optional per-run setting (only allowed after checksum/recheck passes; guarded in UI).

---

## Permissions

- Run container as `99:100` (nobody:users) to match Unraid defaults.
- Ensure mounted shares are writable by that UID/GID.
- If you see `permission denied`:
  - Verify share export/ACLs and ownership.
  - Try adding `:rw` to the mounts.
  - Confirm you didn’t map to `/data/...` in this app (those are *qB container* paths).

---

## Cache / Mover Interaction

- If torrents are paused to let the **mover** clear cache, keep that workflow:
  - You can run **Dry Run** while paused (no file writes).
  - For real migrations at scale, consider disabling the mover temporarily or run during low-activity windows.
- Identity binds (`/mnt/user/...`) let rsync move within the same user share for **hardlink** friendliness.

---

## Troubleshooting

**1) The table shows “Misplaced” incorrectly**  
- Check `GET /api/config` mappings.  
- Save path examples:  
  - OK: `/data/torrents/...`  
  - Misplaced: `/data/...` (not under `/data/torrents/...`)  
  - Custom OK (your setup): `/reseeds/...` (mapped to `/mnt/user/media/reseeds`)

**2) No live log lines**  
- Open `/api/events/stream` directly — you should see:
  ```
  event: state
  data: {"message":"SSE connected"}
  : heartbeat ...
  ```
- If blank: reverse proxy buffering? Ensure:
  - `X-Accel-Buffering: no` (Nginx)
  - No buffering on SWAG/Traefik, or access the container directly.

**3) “Cannot map paths (src=..., dst=...)”**  
- Your qB save path (container) doesn’t match any `container` rule.  
- Add/adjust a mapping rule where `container` prefix matches the save path.

**4) Rsync doesn’t run**  
- On Windows dev box you’ll see: `rsync not found in PATH — dry-run preview only` (expected).  
- On Unraid, rsync is installed in the container image; if you still see this, confirm you’re running the **built image** (not your local venv).

**5) qBittorrent API hangs on pause/recheck**  
- We:  
  - Skip **pause** on dry-run.  
  - Use timeouts on real runs (`5s`) and warn if a call is slow.  
- If your qB WebUI is behind auth/CSRF changes, verify credentials in env.

**6) Long paths push columns off-screen**  
- We switched table to wrap long paths (`break-words`) and widened layout.  
- Hover shows a tooltip with full path.

---

## Security

- Minimal local auth (username/password via `APP_ADMIN_USER`, `APP_ADMIN_PASS`).  
- Put this behind your existing reverse proxy (SWAG/Traefik) if exposing beyond LAN.  
- Credentials to qB Web API are stored as environment variables; scope network exposure accordingly.

---

## Development

**Run backend in venv (Windows example)**
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

**Run frontend**
```bash
cd frontend
npm ci
npm run dev
# open http://localhost:5173
```

**Full container build**
```bash
docker build -t unraid-torrent-helper:dev .
docker run --rm -p 8088:8088 \
  -e QB_URL=http://192.168.1.118:8080 \
  -e QB_USERNAME=admin -e QB_PASSWORD=admin \
  -e APP_MAPPINGS='[{"container":"/data","host":"/mnt/user/torrents"},{"container":"/data/torrents","host":"/mnt/user/media/torrents"}]' \
  -v /mnt/user/torrents:/mnt/user/torrents \
  -v /mnt/user/media/torrents:/mnt/user/media/torrents \
  unraid-torrent-helper:dev
```

---

## Acceptance Tests (quick)

1. **Misplaced detection**  
   - Torrent with save path `/data/<…>` → Shows **Misplaced** with suggested `/data/torrents/<…>`.

2. **Dry-run migration**  
   - Select torrent → **Migrate Selected (dry-run)** → Log shows mapping line, full `rsync --dry-run` command, plan summary, “dry-run complete”.

3. **Real migration**  
   - Disable Dry Run → run migration → files appear under `/mnt/user/media/torrents/...`; qB save path updates; recheck passes.

4. **Fix metadata**  
   - Stuck torrent → **Fix Metadata** → reannounce or replace `.torrent` → recheck → resumes downloading/seeding.

---

## Config Reference

| Env var             | Meaning                                | Default |
|---------------------|----------------------------------------|---------|
| `QB_URL`            | qB Web API URL                         | `http://192.168.1.118:8080` |
| `QB_USERNAME` / `QB_PASSWORD` | qB auth                      | none    |
| `APP_ADMIN_USER` / `APP_ADMIN_PASS` | App login              | `admin` / `change-me` |
| `APP_DATA_DIR`      | App data directory                     | `/config` |
| `APP_MAPPINGS`      | JSON array of `{container,host}` rules | see above |
| `APP_RSYNC_FLAGS`   | rsync flags (string)                   | `-aHAX --info=progress2 --partial --inplace --numeric-ids --preallocate` |
| `APP_MAX_CONCURRENT`| concurrent migrations                  | `2`     |

---