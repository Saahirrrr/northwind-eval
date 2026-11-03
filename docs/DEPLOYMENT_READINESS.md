# Gridbricks Wind Intelligence: Vercel Deployment Readiness

Audit date: **2026-11-02**
Scope: read-only Vercel deployment plan for the existing repository. No code, dependency,
Docker, test, account, or deployment changes were made.

## Executive conclusion

Deploy the application as **two Vercel projects** on the Hobby plan:

1. A static React/Vite frontend project rooted at `frontend/`.
2. A Python Functions backend project rooted at `backend/`.

This keeps the existing frontend and FastAPI boundaries clear, avoids trying to make Nginx
and Docker Compose run inside Vercel, and allows the frontend to call the backend through a
configured HTTPS API origin. The current Docker files remain useful for local/container
verification and still satisfy the challenge's Docker requirement; they are not the Vercel
runtime.

This plan is **not a claim that Vercel Hobby compatibility is proven**. The frontend is
straightforward. The backend requires a small Vercel entrypoint/routing adaptation and a
measured cold-start test with live Elexon data before it can be called deployment-ready.

## Backend deployment discovery correction

The first backend deployment was built successfully but contained no Python Function. The
observed deployment used the repository root (`.`) as the Vercel project root, while the
backend's `pyproject.toml`, `.python-version`, `requirements.txt`, and `app/main.py` are all
under `backend/`. Consequently, Vercel did not inspect the backend entrypoint files or dependency metadata.
The previously configured custom metadata was:

```toml
[tool.vercel]
entrypoint = "app.main:app"
```

This explains the empty deployment and the generated `NOT_FOUND` responses. The custom
metadata syntax was valid, but relying on it while the project root was wrong did not cause
Vercel to discover the backend.

The smallest reliable correction is to set the **backend Vercel project's Root Directory to
`backend`** (or deploy from `backend/` with the CLI) and use the standard root-level
`main.py` entrypoint, which imports the existing `app.main.app` instance. With that project
root, Vercel sees `main.py` as a supported FastAPI entrypoint, reads `requirements.txt`, and
reads `.python-version`. No `api/index.py` adapter, custom entrypoint metadata, or rewrite is
required.

This conclusion is based on the current Vercel documentation accessed **2026-11-02**:

- [Deploy a FastAPI app on Vercel](https://vercel.com/docs/frameworks/backend/fastapi):
  FastAPI applications export a top-level `app`; supported entrypoint filenames include
  `main.py` inside an `app/` directory, and custom modules can use
  `tool.vercel.entrypoint`.
- [Using the Python Runtime with Vercel Functions](https://vercel.com/docs/functions/runtimes/python):
  Python entrypoints may be discovered in an `app/` directory, or explicitly configured with
  `tool.vercel.entrypoint = "module:variable"`.
- [Set the Python version for your Vercel project](https://vercel.com/docs/functions/runtimes/python/python-version):
  `.python-version` is supported and `3.12` is a supported runtime.
- [Python Functions in the `/api` Directory](https://vercel.com/docs/functions/runtimes/python/api-directory):
  `api/index.py` is the file-based `/api` function convention. It is not used because this
  application already uses the documented FastAPI framework entrypoint and owns its `/api/...`
  route prefixes.

Required backend project settings:

| Setting | Required value |
|---|---|
| Root Directory | `backend` |
| Framework preset | FastAPI if detected; otherwise `Other` |
| Python version | `3.12` from `backend/.python-version` |
| Dependency file | `backend/requirements.txt` relative to the project root |
| Entrypoint | `main.py`, exporting the existing `app.main.app` instance |

The project root must be corrected before the next deployment. A root-level `vercel.json`,
rewrite, or duplicate `api/index.py` would add another routing layer and is not required by
the verified FastAPI convention.

## Verified repository architecture

### Frontend

- Root: `frontend/`
- React 18, TypeScript, Vite 5, Tailwind, Recharts, Axios.
- Build command: `npm run build`, which runs `tsc && vite build`.
- Output: `frontend/dist`.
- API client: `frontend/src/api/client.ts`.
- API base: `import.meta.env.VITE_API_BASE_URL || '/api'`.
- Local Vite proxy: `/api` -> `http://localhost:8000`.
- The value is compiled into the browser bundle at build time. A Vercel runtime environment
  variable cannot change an already-built bundle.

### Backend

- Root: `backend/`
- FastAPI application export: `app` in `backend/app/main.py`.
- Routes are registered under `/api`, including health, metadata, accuracy, vintages, and
  provenance endpoints.
- Dependencies are declared in `backend/requirements.txt`.
- Settings use `GRIDBRICKS_` environment variables through Pydantic Settings.
- The FastAPI lifespan calls `await service.load_data()` during process initialization.
- `AnalysisService` stores actuals, forecasts, selected forecasts, analyzer state, and a
  five-minute cache in process memory.
- Elexon requests use `httpx.AsyncClient`, a 60-second request timeout, and up to three
  retries, with bounded backoff for timeout, HTTP, and rate-limit failures.
- Live failures set `data_mode="error"` and do not silently load fixtures.

### Docker and Compose

- `Dockerfile.backend` starts Uvicorn on `0.0.0.0:8000`.
- `frontend/Dockerfile` builds the Vite bundle and serves it with Nginx.
- `frontend/nginx.conf` proxies `/api/` to the Compose hostname `backend:8000`.
- `docker-compose.yml` coordinates the two containers and uses a Docker health check.
- None of the Compose service discovery, Nginx proxying, or fixed container ports is available
  automatically in a Vercel deployment.

## Recommended Vercel project layout

Create two projects from the same repository:

### Project A: frontend

Configure the Vercel project root directory as `frontend/`.

```text
frontend/
  package.json
  vite.config.ts
  index.html
  src/
  dist/                 # generated by Vercel; do not commit
```

### Project B: backend

Configure the Vercel project root directory as `backend/`. The root `main.py` forwarding
module exposes the existing `app/main.py` application. Vercel's documented FastAPI discovery
supports a root-level `main.py`, so an `api/index.py` adapter and custom entrypoint metadata
are not required:

```text
backend/
  app/
    main.py            # existing FastAPI app exporting app
  requirements.txt
  pyproject.toml
  main.py                # imports app.main.app; Vercel entrypoint
```

This is deployment metadata, not a replacement for the existing FastAPI application. It must
not duplicate routes or create a second analysis service.

## Exact Vercel configuration to prepare

### Frontend project settings

| Setting | Value |
|---|---|
| Root directory | `frontend` |
| Framework preset | Vite, or Other if Vite is not detected |
| Install command | `npm ci` |
| Build command | `npm run build` |
| Output directory | `dist` |
| Node version | Use a Vercel-supported Node version compatible with the lockfile; validate the current `package-lock.json` in a preview |
| Environment variable | `VITE_API_BASE_URL=https://<backend-project>.vercel.app/api` |

Do not set backend secrets or `GRIDBRICKS_*` values in `VITE_*` variables. Vite embeds
`VITE_*` values in public browser assets.

### Backend project settings

| Setting | Value |
|---|---|
| Root directory | `backend` |
| Runtime | Vercel Python runtime |
| Dependency file | `requirements.txt` |
| Function entrypoint | `main.py`, forwarding to the existing `app.main.app` |
| Public API base | `https://<backend-project>.vercel.app/api` |

An optional `backend/vercel.json` can make the intended function limit explicit after the
adapter exists:

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "functions": {
    "app/main.py": {
      "maxDuration": 300
    }
  }
}
```

No rewrite is proposed here. The FastAPI application already declares its routes under `/api`,
and a rewrite such as `"/api/:path*" -> "/api"` would discard the requested suffix rather than
preserve the original route. The optional `vercel.json` is a deployment candidate only; the
route mapping must be verified on a Vercel preview before use.

## Backend routing and frontend API calls

The recommended request path is:

```text
Browser
  -> https://<frontend-project>.vercel.app
  -> https://<backend-project>.vercel.app/api/health
  -> FastAPI route /api/health
```

The frontend must be built with the backend URL:

```text
VITE_API_BASE_URL=https://<backend-project>.vercel.app/api
```

The Axios client appends paths such as `/health`, `/analysis/accuracy`,
`/analysis/vintages`, and `/analysis/provenance`. Do not include a trailing slash in the
configured base URL if Axios path joining is changed later; validate the actual generated
requests in the browser network panel.

The existing Nginx `/api` proxy is for Docker Compose only. It cannot resolve the Compose
hostname `backend` on Vercel.

## Required environment variables

### Backend Vercel project

Set these as runtime environment variables:

```text
GRIDBRICKS_USE_FIXTURES=false
GRIDBRICKS_ELEXON_BASE_URL=https://data.elexon.co.uk/bmrs/api/v1
GRIDBRICKS_CORS_ORIGINS=https://<frontend-project>.vercel.app
```

The following existing defaults preserve the challenge scope and should remain unchanged
unless a deliberate methodology decision is documented:

```text
GRIDBRICKS_DELIVERY_START_DATE=2026-01-01
GRIDBRICKS_DELIVERY_END_DATE=2026-01-31
GRIDBRICKS_FORECAST_FETCH_START=2025-12-29T00:00:00Z
GRIDBRICKS_FORECAST_FETCH_END=2026-02-01T00:00:00Z
GRIDBRICKS_CUTOFF_HOUR_UTC=9
GRIDBRICKS_CUTOFF_MINUTES_UTC=0
GRIDBRICKS_CUTOFF_DAYS_BEFORE_DELIVERY=1
```

These names follow the existing Pydantic Settings fields and `GRIDBRICKS_` prefix.

### Frontend Vercel project

Set this as a **build-time** environment variable:

```text
VITE_API_BASE_URL=https://<backend-project>.vercel.app/api
```

No Elexon credential is required by the current public read-only endpoints. Do not add a
credential to the frontend. Do not enable fixture mode in the backend production project.

## Hobby-plan compatibility analysis

Official Vercel documentation inspected for this audit:

- Python runtime and entrypoints:
  <https://vercel.com/docs/functions/runtimes/python>
- Function limits:
  <https://vercel.com/docs/functions/limitations>
- Hobby plan:
  <https://vercel.com/docs/plans/hobby>
- Frontend build configuration:
  <https://vercel.com/docs/builds/configure-a-build>

The current documentation states:

- Hobby is a free plan for personal/non-commercial use subject to Vercel's fair-use terms.
- Hobby Python Functions have a maximum duration of 300 seconds.
- Hobby Functions have a maximum memory of 2 GB.
- Standard Python deployment bundle size is 500 MB uncompressed.
- Functions are request-driven and can be cold-started or scaled to separate instances.

### Can startup preload work on Hobby?

**Possibly, but not verified and not safe to claim as ready.**

The current lifespan preload performs:

1. One FUELHH request with a 60-second timeout and retry policy.
2. One WINDFOR request with a 60-second timeout and retry policy.
3. Validation, normalization, forecast selection, provenance preparation, and analytics setup.

The configured retry/backoff path can consume a substantial portion of a 300-second maximum
duration if Elexon is slow or rate-limits requests. A cold start may therefore exceed practical
latency expectations even though the theoretical Hobby maximum is 300 seconds. A Vercel
Function can also be initialized more than once, so the five-minute in-memory cache is not a
global cache and cannot prevent repeated Elexon retrieval across instances.

The live January retrieval is about 1,488 FUELHH records and 19,856 WINDFOR records. This is
likely within the documented 2 GB memory and 500 MB bundle limits because the data is fetched
at runtime and is not packaged into the deployment, but memory and duration must be measured
on a Vercel preview. The repository has no Vercel runtime measurement.

### Serverless risks

- **Cold starts:** the first request can wait for lifespan preload, and a new instance repeats
  it.
- **Function duration:** Elexon timeout/retry behavior may approach or exceed practical
  request limits during provider slowness.
- **Cache scope:** `_actuals`, `_forecasts`, `_selected`, and `_analyzer` are process-local;
  they are not durable or shared across instances.
- **Concurrent initialization:** separate instances can issue duplicate Elexon fetches.
- **Provider dependency:** all analysis depends on live Elexon availability; no fixture fallback
  occurs when live mode fails.
- **Health semantics:** `/api/health` reports process liveness, while preload errors are logged
  by the lifespan. It must not be treated as proof that live analysis is loaded.
- **CORS:** the backend must allow exactly the deployed frontend origin.
- **Routes:** Vercel routing must preserve all existing `/api/...` paths.
- **Free-plan use:** Hobby's personal/non-commercial and usage terms must be confirmed for the
  intended internship demonstration. Exceeding free quotas may pause or limit further usage;
  there is no paid fallback in this plan.

## One project or two?

### Recommendation: two projects

Two projects are recommended because:

- The frontend and backend already have independent build systems and roots.
- Vite output is static; FastAPI is a Python Function.
- Each project can have the correct runtime-specific environment variables.
- The frontend build can point directly at the backend URL without depending on Nginx.
- Failures and logs are easier to isolate.
- No mixed-root `vercel.json`, cross-runtime rewrites, or monorepo build ordering is required.

### One project: possible but less suitable

A single Vercel project could use a root-level configuration to build `frontend/` and route
`api/` to a Python Function. It would require additional root-level routing/build configuration,
careful inclusion of both dependency trees, and verification that the frontend SPA fallback
does not capture API routes. It would be more compact but increases deployment coupling and
is not the smallest-risk path for this repository.

## Step-by-step deployment procedure

This is a plan only; none of these deployment steps were executed.

1. Confirm the Vercel Hobby account is eligible for the intended personal/non-commercial
   internship demonstration.
2. Set Python 3.12 explicitly for Vercel; the current local Python 3.9 environment is not a
   Vercel-supported runtime.
3. Use the root-level `backend/main.py` forwarding entrypoint and create the backend Vercel
   project with root directory `backend`.
5. Configure the backend runtime variables listed above, especially fixture mode false and the
   exact frontend origin.
6. Deploy a backend preview.
7. Verify `/api/health`, `/api/metadata`, `/api/analysis/accuracy`,
   `/api/analysis/vintages`, and `/api/analysis/provenance`.
8. Record first-request duration, response status, logs, `data_mode`, and Elexon fetch errors.
9. Create the frontend Vercel project with root directory `frontend`.
10. Set `VITE_API_BASE_URL` to the backend preview URL plus `/api`.
11. Deploy a frontend preview.
12. Check browser network requests and CORS for all three dashboard sections.
13. Run the frontend automated tests, backend tests, Ruff, TypeScript check, and production
    build before promoting either project.
14. Repeat the checks using production environment variables and production URLs.
15. Promote only after a refresh, a new cold invocation, and a backend error response have all
    been observed and documented.

## Post-deployment verification

### Commands

```bash
curl -fsS https://<backend-project>.vercel.app/api/health
curl -fsS https://<backend-project>.vercel.app/api/metadata
curl -fsS https://<backend-project>.vercel.app/api/analysis/accuracy
curl -fsS 'https://<backend-project>.vercel.app/api/analysis/vintages?date=2026-01-15&page=1&page_size=5'
curl -fsS 'https://<backend-project>.vercel.app/api/analysis/provenance?date=2026-01-15&page=1&page_size=5'
```

### Manual checks

- Frontend loads over HTTPS with no blank SPA route or asset failures.
- Accuracy KPI values and charts render.
- Vintage Inspector shows eligible, selected, and post-cutoff vintages.
- Provenance shows FUELHH/WINDFOR records, raw values, and missing-value distinctions.
- Browser requests target the backend URL, not `localhost` or the Compose hostname `backend`.
- Backend CORS allows the frontend origin and rejects unintended origins.
- Metadata reports `data_mode=live`, the January 2026 period, and the configurable D-1 09:00
  UTC policy.
- Elexon failures produce an explicit UI/API error, never fixture-shaped results.
- Refreshing after an idle period still returns consistent metrics.
- A new function instance does not select a post-cutoff forecast or alter metric methodology.
- Vercel logs contain no secrets and no unexpected startup exceptions.

## Unresolved decisions and blockers

1. **Python runtime mismatch:** local Python 3.9 is not among Vercel's currently supported
   Python versions; select Python 3.12 and run the complete backend suite there.
2. **Routing not yet proven:** verify the existing `app/main.py` discovery or explicit
   the root-level `main.py` entrypoint on a Vercel preview; do not add the path-dropping rewrite.
3. **Cold-start duration unknown:** measure first and warm requests with live Elexon data.
4. **Hobby eligibility:** confirm the intended internship demonstration complies with Hobby
   personal/non-commercial terms and current usage limits.
5. **No persistent cache:** repeated cold starts can repeat Elexon calls; adding a database,
   Redis, or another provider is outside this plan and prohibited by the current scope.
6. **Readiness semantics:** `/api/health` does not currently prove data preload success.
7. **Frontend URL is build-time:** changing the backend project URL requires a frontend
   rebuild.
8. **Current Docker verification is separate:** Docker Compose remains local/container
   evidence, not Vercel evidence.
9. **No deployment performed:** there is no public URL or verified Vercel result.

## Vercel Hobby Technical Feasibility Review

Review date: **2026-11-02**. Official Vercel documentation was accessed on this date.

### Decision

**Classification: READY AFTER SMALL ADAPTATIONS.**

There is no fundamental Hobby-plan blocker identified for this dataset size or dependency
set. However, the current repository is not ready to deploy unchanged:

1. The repository's local Python target is 3.9, while current Vercel documentation lists
   Python 3.12, 3.13, and 3.14 as supported. Vercel defaults to 3.12 when no supported version
   is declared.
2. The current worst-case sequential Elexon retry path exceeds Hobby's 300-second function
   maximum by a wide margin.
3. FastAPI entrypoint discovery and preservation of the existing `/api/...` prefixes must be
   verified in a Vercel preview.

The smallest safe deployment changes are to select Python 3.12, explicitly configure
the root-level `main.py` entrypoint, bound the live-fetch retry budget
for the serverless deployment, and verify routing and cold-start behavior. These changes do
not alter the forecast cutoff, matching, or metric methodology. They were not implemented in
this read-only review.

### Exact startup-duration calculation

The calculation below follows the current source:

- `backend/app/main.py` awaits `service.load_data()` in the FastAPI lifespan, sequentially
  before yielding.
- `backend/app/services/analysis_service.py` awaits FUELHH, then WINDFOR; the two requests
  are not concurrent.
- `backend/app/core/config.py` defaults `elexon_timeout_seconds` to 60 and
  `elexon_max_retries` to 3.
- `backend/app/clients/elexon_client.py` loops `range(max_retries + 1)`, therefore allowing
  4 attempts.
- On every timeout, HTTP 5xx, or HTTP error, the client sleeps after the attempt using
  `min(2 ** attempt * 2, 30)`.

For one request in the worst case, where all four attempts reach the 60-second timeout:

```text
request timeouts = 4 attempts * 60 seconds = 240 seconds
backoff sleeps   = (2 + 4 + 8 + 16) seconds = 30 seconds
one request      = 240 + 30 = 270 seconds
```

The final-attempt sleep is included because the exception handlers sleep before the loop
terminates and raises `ElexonClientError`. Since FUELHH and WINDFOR run sequentially:

```text
FUELHH worst case  = 270 seconds
WINDFOR worst case = 270 seconds
preload I/O total  = 270 + 270 = 540 seconds
```

Selection, Pydantic parsing, normalization, provenance construction, and analyzer setup run
after successful retrieval. Their duration is not bounded by a configured timeout, so the
overall worst case is **at least 540 seconds plus CPU/parsing time**, not exactly 540 seconds.
This exceeds the documented Hobby maximum of 300 seconds by **at least 240 seconds**.

If both calls succeed on their first attempt, their network wait is bounded by approximately
`60 + 60 = 120 seconds`, followed by processing. That is a best-case timeout-bound, not a
performance guarantee. A retry budget of one retry per dataset would bound the timeout/error
path to:

```text
2 attempts * 60 seconds + (2 + 4) seconds = 126 seconds per dataset
2 sequential datasets = 252 seconds, plus processing
```

Even that configuration must be measured because provider response, JSON parsing, and Vercel
initialization time consume part of the 300-second limit. A deployment-safe alternative is to
avoid doing both live fetches in lifespan initialization and load on demand, but the first
analysis request would still need a bounded fetch budget. No such change was made.

### FastAPI entrypoint, lifespan, and routing

Documented facts:

- Vercel's FastAPI guide says it looks for a FastAPI instance named `app` at supported
  entrypoints, including `main.py` inside an `app/` directory. This repository has exactly
  `backend/app/main.py` with a top-level `app`.
- This repository now provides `backend/main.py` as the standard root-level entrypoint. It
  imports and exposes the existing `app.main.app` instance without creating a second app.
- Vercel's FastAPI documentation links to the official announcement that FastAPI lifespan
  events are supported. The existing `@asynccontextmanager` lifespan is therefore a supported
  mechanism in principle.
- The application declares all routes with the `/api` prefix. Vercel's FastAPI integration
  must deliver the original request path to that ASGI application.

The previously proposed `api/index.py` adapter is not required by the current FastAPI guide
when the project root is `backend`, because `main.py` is a supported root-level entrypoint.

Routing conclusion:

- Do **not** use the earlier candidate rewrite `"/api/:path*" -> "/api"`; it does not preserve
  the suffix such as `/health` or `/analysis/accuracy`.
- Prefer automatic FastAPI routing with `main.py` and no rewrite.
- Confirm on a preview that `/api/health`, `/api/metadata`, `/api/analysis/accuracy`,
  `/api/analysis/vintages`, and `/api/analysis/provenance` all reach the existing FastAPI
  routes. The exact interaction between a project-root Python Function and these prefixed
  paths remains preview-dependent and is not proven by local Docker routing.

### Dependency, Python, and bundle review

The backend requirements are:

```text
fastapi, uvicorn[standard], httpx, pydantic, pydantic-settings,
python-dateutil, numpy, pytest, pytest-asyncio, pytest-httpx, ruff
```

- Vercel supports `requirements.txt` dependency installation, so the manifest format is
  supported.
- FastAPI, Pydantic, HTTPX, and python-dateutil are pure Python or have standard supported
  wheels.
- NumPy is the only notable native/binary dependency. It must install for the selected Vercel
  Python version and architecture; this is a preview-build check, not a repository-proven
  fact.
- `pytest`, `pytest-asyncio`, `pytest-httpx`, and `ruff` are test/development dependencies
  currently included in the production requirements file. They increase install/bundle size
  but are not expected to approach the documented 500 MB uncompressed Python bundle limit.
  Removing them would be an unrelated dependency change and is not recommended as part of
  this read-only audit.
- `backend/pyproject.toml` currently contains pytest/Ruff configuration only; it does not
  declare `requires-python` or `tool.vercel.entrypoint`.
- The local environment uses Python 3.9. Current Vercel documentation supports 3.12–3.14,
  so Python 3.12 must be selected and the backend suite rerun there before deployment.
- With the backend project root set to `backend`, imports such as `from app...` resolve from
  the project root. This is expected but must be confirmed by the preview build.

The runtime data is fetched after deployment rather than bundled. The January live payload
(1,488 FUELHH records and 19,856 WINDFOR records) therefore affects runtime memory, not
deployment bundle size. No measured Vercel memory profile exists. The documented 2 GB Hobby
memory and 500 MB standard Python bundle limits are not demonstrated to be exceeded, but
preview measurement remains required.

### Hobby eligibility

Vercel's current Hobby documentation describes Hobby as free and intended for personal
projects, and links to fair-use terms restricting Hobby to personal, non-commercial use.
A publicly accessible internship challenge demonstration built as an individual's educational
project is **likely** to fit that description when it is not used to sell a service, support a
business, or provide commercial hosting. This is not a legal determination, and the user
should confirm the account's current terms and intended use before deployment.

The plan must also remain within current monthly usage limits. This application has no
scheduled jobs and is expected to receive demonstration traffic, but each cold start can
make two external Elexon requests. Usage and fair-use behavior must be monitored without
assuming unlimited free operation.

### Review evidence and access dates

Official documentation reviewed on **2026-11-02**:

- [Deploy a FastAPI app on Vercel](https://vercel.com/docs/frameworks/backend/fastapi)
  (FastAPI entrypoints, `app` export, `tool.vercel.entrypoint`, lifespan support reference).
- [Using the Python Runtime with Vercel Functions](https://vercel.com/docs/functions/runtimes/python)
  (ASGI runtime, supported dependency manifests, Python Function behavior).
- [Set the Python version for your Vercel project](https://vercel.com/docs/functions/runtimes/python/python-version)
  (supported Python 3.12, 3.13, and 3.14).
- [Vercel Functions Limits](https://vercel.com/docs/functions/limitations)
  (Hobby 300-second maximum duration, 2 GB memory, 500 MB standard Python bundle).
- [Vercel Hobby Plan](https://vercel.com/docs/plans/hobby)
  (free plan scope, personal/non-commercial terms, and plan constraints).

### Smallest safe change set

Before deployment, without changing analysis methodology:

1. Select Python 3.12 in the backend Vercel project and validate NumPy installation.
2. Use the root-level `main.py` forwarding entrypoint, which exposes the existing
   `app.main.app` instance.
3. Do not apply the path-dropping rewrite; verify the existing `/api` routes on preview.
4. Bound the serverless Elexon retry/timeout budget so the sequential worst case stays below
   300 seconds with processing headroom, or replace lifespan preload with a bounded lazy-load
   strategy. This is the main functional deployment blocker.
5. Set exact frontend CORS and build-time API-origin variables.
6. Run a preview cold-start test with live Elexon data, record duration and memory, then run
   all existing automated checks under Python 3.12.

Until these checks pass, the correct status is **READY AFTER SMALL ADAPTATIONS**, not READY.

## Files inspected

- `README.md`
- `docs/PROJECT_AUDIT.md`
- `docs/MANUAL_TEST_REPORT.md`
- `docs/JANUARY_2026_DATA_VALIDATION.md`
- `docs/DEVELOPMENT_HANDOVER.md`
- `docker-compose.yml`
- `Dockerfile.backend`
- `frontend/Dockerfile`
- `frontend/nginx.conf`
- `.env.example`
- `backend/app/main.py`
- `backend/app/core/config.py`
- `backend/app/api/routes.py`
- `backend/app/services/analysis_service.py`
- `backend/app/clients/elexon_client.py`
- `backend/requirements.txt`
- `backend/pyproject.toml`
- `frontend/src/api/client.ts`
- `frontend/vite.config.ts`
- `frontend/package.json`
