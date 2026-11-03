# DecisionIQ / Gridbricks Development Handover

## Current project status

The workspace currently contains a working wind forecast evaluation slice rather than the
DecisionIQ HR analytics architecture described in the supplied project brief. The implemented
product is named **Gridbricks Wind Intelligence** and evaluates January 2026 UK wind forecasts.
There is no Git repository metadata or roadmap documentation in this workspace, so the current
source code and tests are the available source of truth.

## Architecture

- **Backend:** Python, FastAPI, Pydantic Settings, and an in-memory analysis service.
- **Data:** Elexon BMRS `FUELHH` actual wind generation and `WINDFOR` forecasts, with local
  fixture fallback.
- **Domain logic:** cutoff-based forecast vintage selection and accuracy analytics.
- **Frontend:** React, Vite, TypeScript, Tailwind CSS, Recharts, and Axios.
- **API:** health, metadata, overview, series, accuracy, and vintage endpoints under `/api`.

The current implementation does not contain PostgreSQL, pgvector, LangGraph, Gemini, natural
language-to-SQL, multi-agent orchestration, calibration, abstention, anomaly detection, or
scenario simulation modules.

## Completed implementation

- Elexon client with response normalization and retry/error handling.
- Configurable D-1 forecast cutoff and latest-eligible-vintage selection.
- Local fixture fallback for offline development.
- MAE, RMSE, MBE, maximum and median absolute error, daily/hourly breakdowns, and error
  distribution analytics.
- FastAPI endpoints and backend unit/API tests.
- Frontend API client, shared layout, overview page, and forecast-vs-actual series page.
- Missing frontend React entrypoint added during this handover so the existing application can
  build.
- Accuracy Dashboard connected to the existing accuracy and series endpoints, with KPI cards,
  generation comparison, absolute-error, and error-distribution charts.
- Forecast Vintage Inspector connected to `/api/analysis/vintages`, exposing deterministic,
  chronologically ordered WINDFOR vintages, cutoff eligibility, selected status, and reasons.
- Data Provenance page connected to `/api/analysis/provenance`, with raw source payloads,
  composite identifiers, interval mapping, transformation explanations, and bounded filtering.
- End-to-end January 2026 live Elexon validation completed and documented in
  `docs/JANUARY_2026_DATA_VALIDATION.md`; live FUELHH and WINDFOR counts, cutoff audit, and
  cross-feature invariants are recorded there.
- Frontend automated tests added with Vitest, jsdom, and Testing Library. They cover metric
  rendering, chart data, vintage status/filter/pagination interactions, provenance expansion,
  missing/duplicate indicators, loading/error/empty/partial states, and shared observation values.
- Reproducible Docker deployment assets added: backend and frontend images, Compose
  orchestration, health checks, same-origin Nginx API proxy, `.env.example`, and deployment
  documentation. Fixture mode remains explicitly disabled by default.
- Full engineering audit completed in `docs/PROJECT_AUDIT.md`. A critical implicit fixture
  fallback was removed; live Elexon failures now produce an explicit error mode instead of
  presenting local sample data as live analysis.

## Partially completed features

- Frontend tests mock the API client and chart primitives in test code; browser-level E2E tests
  and production API contract tests are not yet present.
- Backend response models exist but are not consistently used as FastAPI response models.
- Fixture loading skips invalid records silently and reports only a generic fixture warning.
- The project brief and the current implementation describe different products and research
  scopes; this discrepancy must be resolved before adding DecisionIQ-specific modules.

## Known bugs and validation status

- The initial frontend build failed because `frontend/src/main.tsx` was missing; this is fixed
  in the current handover.
- A test run from the workspace root reports seven API test failures because pytest does not
  load `backend/pyproject.toml` from that location, leaving the async client fixture as an
  async generator. Run pytest from `backend/` to use the configured `asyncio_mode = "auto"`.
- No Git history is available in this workspace, so the previous development milestone and
  unfinished task cannot be recovered from commits.
- Docker build and Compose startup could not be executed because the Docker CLI is not installed
  in the current environment (`docker: command not found`).
- The audit regression suite increased backend coverage to 59 passing tests. Frontend coverage
  remains 8 passing tests across 3 files.

## Forecast Vintage Inspector API

`GET /api/analysis/vintages?date=YYYY-MM-DD&page=1&page_size=48` returns bounded delivery
interval records. Each record contains the selected forecast compatibility fields plus `vintages`,
where each item includes `publish_time`, `generation_mw`, `eligible`, `selected`,
`selection_reason`, and `duplicate_publication`. Vintages are associated by delivery interval,
normalized to UTC, sorted chronologically, and deduplicated by publication timestamp. The
selected item is always the latest publication at or before the configured project evaluation
policy of D-1 09:00 UTC. This boundary is not presented as a universal or official UK market
deadline.
Missing actuals remain `null`; zero generation remains a valid numeric value.

## Data Provenance API

`GET /api/analysis/provenance?date=YYYY-MM-DD&settlement_period=1..48&page=1&page_size=50`
returns bounded provenance rows for FUELHH and WINDFOR. Optional `delivery_interval` filters an
exact ISO UTC interval. Each row includes the original validated source payload, deterministic
`source_id`, raw and normalized MW values, UTC delivery/publication/cutoff timestamps, matching
status, eligibility and selection status, duplicate/missing indicators, forecast error when
available, and a transformation explanation.

FUELHH settlement date plus one-indexed settlement period is converted to the UTC half-hour
interval used by analysis. WINDFOR `startTime` is normalized to that same UTC interval;
half-hour intervals may use the existing hourly fallback. Source IDs are SHA-256 composites of
the available source fields because the Elexon records do not provide a stable ID in this
integration. Missing rows are explicit markers and are not presented as source observations.

## January 2026 validation

The direct live API validation retrieved 1,488 FUELHH records and 19,856 WINDFOR records with
no API or parse errors. The selector produced 1,488 selected forecasts, 1,488 matched intervals,
100.0% coverage, and zero post-cutoff selections. See
`docs/JANUARY_2026_DATA_VALIDATION.md` for exact query ranges, retrieval timing, metrics, and
limitations.

## Current milestone

The current milestone is deployment readiness for the Gridbricks wind forecast evaluation
dashboard foundation, including reproducible Docker assets and documented runtime configuration.

## Exact resume point

Install Docker Engine or Docker Desktop and execute the deployment validation commands below.
Keep the existing cutoff-selection and analytics contracts unchanged.

## Next three implementation tasks

1. Run Docker build, Compose startup, health, page, restart, and log checks in an environment
   with Docker installed.
2. Add browser-level E2E tests if deployment-style validation becomes necessary.
3. Reconcile the supplied DecisionIQ research roadmap with the current Gridbricks implementation.

## Frontend test commands and results

Run `cd frontend && npm test` for the one-shot Vitest suite, or
`cd frontend && npm run test:watch` during development. Production validation remains
`cd frontend && npm run build`. The current suite has **8 passing tests across 3 files**.
Coverage collection is not configured; tests use API-client and chart mocks only inside test
modules, with no production fixture flow changes.

## Deployment readiness validation

Executed successfully:

```text
cd frontend && npm test                         # 8 passed across 3 files
cd backend && ../.venv/bin/py.test -q           # 59 passed
cd backend && ../.venv/bin/ruff check app tests # All checks passed
cd frontend && npm run build                    # Passed; existing chunk-size warning only
```

The local backend smoke test passed with fixture mode disabled. It returned `status=ok`,
`data_mode=live`, and the January 2026 evaluation period; startup retrieved 1,488 FUELHH and
19,856 WINDFOR records without API errors.

Not executed because Docker is unavailable:

```text
docker compose config
docker compose build --no-cache
docker compose up -d
docker compose ps
docker compose logs --tail=100
```

The exact deployment configuration is in `docker-compose.yml`, `Dockerfile.backend`,
`frontend/Dockerfile`, and `frontend/nginx.conf`. The remaining deployment check must verify
frontend access through port 8080, `/api/health` through the Nginx proxy, all three dashboard
pages, restart behavior, and absence of startup exceptions.

After deployment verification, reconcile the supplied DecisionIQ roadmap with this Gridbricks
implementation before introducing any new AI, database, or research infrastructure.
