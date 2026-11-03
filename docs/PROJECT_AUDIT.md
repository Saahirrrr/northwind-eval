# Gridbricks Wind Intelligence project audit

Audit scope: complete source, tests, configuration, deployment assets, and documentation
against the Gridbricks challenge brief. Audit performed 2026-11-02. No deployment was
claimed because the Docker CLI is unavailable in the current environment.

## Summary

The project implements the required narrow product slice: React frontend, Python/FastAPI
backend, Elexon-only FUELHH/WINDFOR ingestion, January 2026 evaluation, D-1 09:00 UTC
configurable selection, accuracy metrics, vintage inspection, provenance, automated tests,
and Docker configuration. One critical data-integrity defect was found and corrected:
live API failures could silently switch a production-configured service to local fixtures.

## Findings and corrections

| Severity | Finding | Affected files | Resolution |
|---|---|---|---|
| Critical | With `use_fixtures=false`, a live Elexon failure fell back to local sample data, allowing a deployment to look functional without live observations. | `backend/app/services/analysis_service.py` | Removed implicit fallback. Live failures now set `data_mode=error`, preserve the error, and return no fabricated analysis. Fixture loading remains explicit only when `GRIDBRICKS_USE_FIXTURES=true`. Added regression coverage. |
| High | Docker runtime assets did not exist before this audit milestone. | `Dockerfile.backend`, `frontend/Dockerfile`, `docker-compose.yml`, `frontend/nginx.conf` | Added reproducible two-service Compose deployment, health checks, backend dependency, and same-origin `/api` proxy. Runtime verification remains pending because Docker is unavailable. |
| High | Frontend API configuration was fixed to `/api` and the Vite proxy was the only alternate path. | `frontend/src/api/client.ts`, `frontend/vite.config.ts` | Added build-time `VITE_API_BASE_URL`, defaulting safely to `/api`; development proxy remains localhost-only. |
| Medium | API routes had response models only for the newer accuracy, vintage, and provenance endpoints. | `backend/app/api/routes.py`, `backend/app/schemas/api.py` | Existing behavior is preserved. The newer analytical contracts are typed; overview, series, metadata, and health remain legacy untyped response shapes and are documented as a maintainability limitation. |
| Medium | Fixture parsing skipped invalid records without counts or details. | `backend/app/services/analysis_service.py` | No production behavior change was made during this audit because fixture mode is explicit and test fixtures are not production data. This remains a follow-up observability improvement. |
| Medium | Analysis data is in memory and reloads after restart. | `backend/app/services/analysis_service.py` | Documented limitation; persistence is outside the challenge scope. |
| Low | The frontend contained an unreachable “Coming next” placeholder branch after all navigation tabs were implemented. | `frontend/src/main.tsx` | Replaced with a safe overview fallback and removed unfinished UI copy. |
| Low | No repository-level `.gitignore` was present at audit start. | repository root | Added `.gitignore` covering environment files, Python/Node dependencies, caches, builds, and logs. |

## Analytical audit

- **Ingestion:** FUELHH is requested with `fuelType=WIND`; WINDFOR is queried over the
  pre/post publication window configured for January delivery. Pydantic validation preserves
  null generation values, and settlement periods are converted to UTC half-hour starts.
- **Timezone:** naive source timestamps are explicitly treated as UTC; aware timestamps are
  normalized to UTC. The selector normalizes publication timestamps before comparison.
- **Selection:** forecasts are grouped by delivery interval; under the configurable project
  evaluation policy, eligible records satisfy
  `publish_time <= cutoff`, including the exact cutoff boundary. The latest eligible
  publication is selected. Duplicate publication timestamps are deduplicated
  deterministically in the vintage detail path.
- **Metrics:** AccuracyAnalyzer deduplicates selected intervals, requires both non-null
  values, recomputes `forecast - actual`, and uses the same matched list for MAE, RMSE,
  MBE, median/max absolute error, sample size, and coverage.
- **Cross-feature consistency:** backend tests verify that Accuracy, Vintage Inspector, and
  Provenance expose the same selected forecast, actual, and error semantics.
- **Missing and zero values:** missing values remain null and are excluded; zero is retained
  as a valid numeric generation value.

No analytical correction was made because the cutoff and metric results were already
consistent with the brief and the live validation evidence.

## Product and challenge coverage

### Satisfied

- React frontend and Python backend.
- Elexon-only national GB wind scope.
- January 2026 FUELHH actuals and WINDFOR forecasts.
- Matching 30-minute delivery intervals.
- Configurable D-1 09:00 UTC policy with exact-boundary and no-lookahead tests.
- Accuracy Dashboard, Vintage Inspector, and Data Provenance views.
- Loading, error, empty, and partial-data states.
- Dockerfiles, Compose, health checks, and safe environment template.
- Frontend tests, backend tests, Ruff, and production build.
- Explicit AI-tool disclosure and no fabricated production values.

### Partial or pending

- Docker build, Compose startup, container health, proxy, restart, and log checks are
  pending because `docker` is not installed.
- No public Vercel/Heroku deployment URL exists; deployment is intentionally not claimed.
- Browser-level E2E tests are not included.
- Fixture invalid-record reporting and response typing for legacy endpoints could be improved.
- The in-memory cache is not durable.

## Security and configuration

No API keys or committed credentials were found. `.env.example` contains only public
configuration and placeholders. Production Compose defaults fixture mode to false, exposes
only the frontend host port, and keeps the backend on the internal Compose network.
CORS is configurable through `GRIDBRICKS_CORS_ORIGINS`; the browser normally uses the
same-origin proxy. API exception details remain an internal logging concern for future
hardening, but no secret-bearing configuration is present.

## Commands executed

```text
cd frontend && npm test                         # 8 passed across 3 files
cd backend && ../.venv/bin/py.test -q           # 59 passed after audit regression test
cd backend && ../.venv/bin/ruff check app tests # All checks passed
cd frontend && npm run build                    # Passed; existing chunk-size warning only
```

Docker commands were not executed successfully because the environment reports
`docker: command not found`. The exact pending commands are:

```text
docker compose config
docker compose build --no-cache
docker compose up -d
docker compose ps
docker compose logs --tail=100
```

## Recommendation

The codebase is ready for the separate manual testing phase, with Docker runtime
verification as an explicit prerequisite for deployment testing. Manual testing should
not treat Docker as verified until the pending Compose commands and page/API/restart checks
have been executed on a machine with Docker installed.
