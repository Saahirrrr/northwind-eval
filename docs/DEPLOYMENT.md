# Deployment

## Local Docker deployment

Prerequisites: Docker Engine or Docker Desktop with Compose.

```bash
cp .env.example .env
docker compose config --quiet
docker compose build --no-cache
docker compose up -d
docker compose ps
curl -fsS http://localhost:8080/
curl -fsS http://localhost:8080/api/health
curl -fsS http://localhost:8080/api/metadata
docker compose logs --tail=100
docker compose down
```

Compose uses Nginx for the browser-facing frontend and an internal backend service. The
backend defaults to live Elexon data; fixtures must be enabled explicitly for offline
development.

## Vercel deployment

Use two projects from the same source:

### Backend project

- Root directory: `backend`
- Python: 3.12 from `.python-version`
- Entrypoint: root `main.py`, forwarding to `app.main.app`
- Runtime dependencies: `requirements.txt` and `pyproject.toml`

Required runtime variables:

```text
GRIDBRICKS_USE_FIXTURES=false
GRIDBRICKS_ELEXON_BASE_URL=https://data.elexon.co.uk/bmrs/api/v1
GRIDBRICKS_ELEXON_TIMEOUT_SECONDS=20
GRIDBRICKS_ELEXON_MAX_RETRIES=1
GRIDBRICKS_CORS_ORIGINS=https://<frontend-domain>
```

Example user-run command (do not put secrets in shell history):

```bash
cd backend
npx vercel deploy --prod --yes --project <backend-project>
```

The first production deployment may be required by the Vercel project state. The project
owner must authorize and execute it.

### Frontend project

- Root directory: `frontend`
- Build command: `npm run build`
- Output directory: `dist`
- Build variable: `VITE_API_BASE_URL=https://<backend-domain>`

The API client adds `/api` exactly once, so the variable may be an origin or an origin
already ending in `/api`.

```bash
cd frontend
npx vercel deploy --prod --yes --project <frontend-project>
```

## Post-deployment checks

```bash
export BACKEND_URL="https://<backend-domain>"
curl -fsS "$BACKEND_URL/api/health"
curl -fsS "$BACKEND_URL/api/metadata"
curl -fsS "$BACKEND_URL/api/analysis/overview"
curl -fsS "$BACKEND_URL/api/analysis/accuracy"
curl -fsS "$BACKEND_URL/api/analysis/series?date_from=2026-01-15&date_to=2026-01-15"
curl -fsS "$BACKEND_URL/api/analysis/vintages?date=2026-01-15&page=1&page_size=5"
curl -fsS "$BACKEND_URL/api/analysis/provenance?date=2026-01-15&page=1&page_size=5"
```

Also verify in a browser:

- Frontend requests use `https://<backend-domain>/api/...`.
- CORS allows exactly the frontend origin.
- Metadata reports live mode, not fixtures.
- Accuracy, vintages, and provenance pages load.
- Elexon failures show an explicit error state.
- Cold and warm requests are observed and recorded; no uptime or latency guarantee is
  claimed by this repository.

## Operational limitations

Vercel instances have independent in-memory caches and may cold-start with Elexon preload.
The local async initialization lock coordinates callers within one process only. No persistent
storage or shared cache is configured.
