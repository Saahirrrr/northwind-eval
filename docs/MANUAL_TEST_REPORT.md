# Gridbricks Wind Intelligence manual test report

Test date: **2026-11-02**
Project: `Gridbricks Wind Intelligence`
Scope: local functional, integration, live-data, resilience, and visual testing. No deployment
or publication was performed.

## 1. Environment

| Item | Result |
|---|---|
| Python | 3.9.6 |
| Node.js | v22.23.1 |
| npm | 10.9.8 |
| Backend dependencies | Installed; local `.venv` used |
| Frontend dependencies | Installed; `node_modules` present |
| Backend | `127.0.0.1:8000` |
| Frontend | `127.0.0.1:5173` |
| Fixture mode | Disabled; live mode confirmed through `/api/metadata` |
| Docker | Not installed |

The `.env.example` variables were reviewed. No secret values were printed or included in this
report.

## 2. Startup and connectivity

| Test | Status | Evidence |
|---|---|---|
| Start backend with documented Uvicorn command | PASS | Startup completed without exceptions |
| Start frontend with documented Vite command | PASS | Vite ready in 205 ms |
| Backend health endpoint | PASS | `/api/health` returned `status=ok` |
| Frontend reaches backend through Vite proxy | PASS | `http://127.0.0.1:5173/api/health` returned 200 |
| Live mode confirmed | PASS | Metadata returned `data_mode=live` |
| No unexpected fixture fallback | PASS | Logs show direct Elexon retrieval and `Data loaded successfully (mode: live)` |

Commands:

```text
cd backend && ../.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
cd frontend && npm run dev -- --host 127.0.0.1 --port 5173
```

## 3. Docker verification

| Test | Status | Result |
|---|---|---|
| Docker installed in this execution environment | BLOCKED | `docker: command not found` |
| `docker compose config --quiet` after this correction | BLOCKED | Docker unavailable here |
| `docker compose build --no-cache` after this correction | BLOCKED | Docker unavailable here |
| Compose startup/health checks after this correction | BLOCKED | Docker unavailable here |
| Frontend/API/restart checks after this correction | BLOCKED | Docker unavailable here |

The user reported successful pre-correction Docker verification on macOS Apple Silicon:
Compose configuration, no-cache image build, healthy containers, frontend HTTP 200,
`/api/health` HTTP 200, `/api/metadata` HTTP 200, Nginx proxying, live Elexon counts, and
manual UI checks. Those results are retained as user-provided prior verification, not as
independently re-executed results for this correction pass.

## 4. Live Elexon verification

| Check | Status | Result |
|---|---|---|
| FUELHH request | PASS | 1,488 `WIND` records retrieved |
| WINDFOR request | PASS | 19,856 records retrieved |
| January expected intervals | PASS | 1,488 half-hour intervals |
| Live data mode | PASS | `live`; no fixture fallback |
| API/parsing errors | PASS | No API or parse errors in startup logs |
| Missing generation values | PASS | 0 in the live validation result |
| Duplicate observations | PASS | 0 in the live validation result |
| Publication window | PASS | 2025-12-29T00:00:00Z to 2026-02-01T00:00:00Z |
| Reference metrics | PASS | Exact match to validation report |
| Docker live counts before this correction | USER-REPORTED | FUELHH 1,488; WINDFOR 19,856; matched 1,488/1,488; coverage 100% |

Observed metrics:

```text
MAE: 2,145.17 MW
RMSE: 2,615.81 MW
MBE: +1,851.90 MW
Median absolute error: 1,795.50 MW
Maximum absolute error: 6,894 MW
Matched intervals: 1,488
Coverage: 100.0%
```

## 5. Accuracy Dashboard

| Test | Status | Result |
|---|---|---|
| Dashboard loads in browser | PASS | KPI page rendered with live values |
| KPI values populated | PASS | Values matched live API metrics |
| Actual/forecast series | PASS | Chart section rendered |
| Absolute-error timeline | PASS | Rendered in dashboard |
| Error distribution | PASS | Histogram section rendered |
| MW units and dates | PASS | Visible in headings, cards, and chart labels |
| MBE sign convention | PASS | Positive overforecast explanation visible |
| Matched count/coverage | PASS | 1,488 and 100.0% displayed |
| Loading state | PASS | Accessible `Loading` status observed during fetch |
| Error state | PASS | Retrieval notice and Retry button rendered when backend stopped |
| Empty/partial states | PASS | Covered by automated frontend tests |

## 6. Forecast Vintage Inspector

| Test | Status | Result |
|---|---|---|
| Page navigation and load | PASS | Live page rendered |
| Delivery date filter | PASS | 2026-01-15 loaded 48 intervals |
| Publication ordering | PASS | Rows displayed chronologically |
| Selected vintage | PASS | 2026-01-14 07:30 UTC selected for SP1 |
| Eligible-not-selected status | PASS | Visible with rationale |
| Post-cutoff status | PASS | Visible with exclusion rationale |
| Cutoff visibility | PASS | D-1 at 09:00 UTC shown |
| Actual distinction | PASS | Actual shown separately in MW |
| Pagination | PASS | Page and interval filtering verified through API and UI |
| Comparison chart | PASS | Forecast-by-publication chart rendered |
| All selected vintages no-lookahead | PASS | 1,488 records audited; 0 post-cutoff selections |
| Exact boundary | PASS | 09:00 eligible; 09:01 excluded |

## 7. Data Provenance

| Test | Status | Result |
|---|---|---|
| Page navigation and load | PASS | Live page rendered |
| FUELHH records | PASS | Dataset badge, raw payload, and normalized value visible |
| WINDFOR records | PASS | Publication and delivery fields visible |
| Raw-record expansion | PASS | Expanded raw JSON displayed |
| Raw/normalized MW values | PASS | Values shown separately |
| UTC timestamps | PASS | Delivery, publication, and cutoff displayed in UTC |
| Source IDs | PASS | Deterministic dataset-prefixed IDs visible |
| Matching/selection indicators | PASS | Statuses visible |
| Duplicate/missing indicators | PASS | UI/API fields present; no live duplicates or missing values observed |
| Filters and pagination | PASS | Date, settlement period, and bounded records verified |

## 8. Cross-page consistency

| Test | Status | Result |
|---|---|---|
| Five delivery intervals compared | PASS | Series, Vintage Inspector, and Provenance agreed |
| Actual values consistent | PASS | All five matched |
| Forecast values consistent | PASS | All five matched |
| Error calculation consistent | PASS | `forecast - actual` matched |
| UTC normalization | PASS | `Z` and `+00:00` representations were equivalent |
| Display filter changes metrics | PASS | Accuracy endpoint is independent of vintage/provenance filters |

## 9. Error and resilience testing

| Test | Status | Result |
|---|---|---|
| Backend unavailable | PASS | Frontend displayed “Data Retrieval Notice” and Retry |
| Backend restart | PASS | Backend reloaded live Elexon data and returned healthy |
| Invalid date filter | PASS | API returned structured HTTP 422 validation response |
| Empty/missing fixture cases | PASS | Covered by backend and frontend automated tests |
| Malformed source records | PASS | Covered by Elexon client tests |
| Refresh during loading | NOT TESTED | No separate race-condition test performed |
| External API failure without fixture mode | PASS | Regression test confirms explicit error mode; no implicit fixture fallback |

## 10. Visual/usability review

| Test | Status | Result |
|---|---|---|
| Desktop layout | PASS | Overview, Accuracy, Vintage, and Provenance screenshots captured |
| Narrower viewport | PASS | 900px viewport had no horizontal overflow |
| Navigation | PASS | All five navigation views reachable |
| Labels/units/time formatting | PASS | MW and UTC labels visible |
| Placeholder content | PASS | No “Coming next” placeholder observed |
| Screenshots | PASS | Saved below |
| Browser console clean before correction | FAIL | Recharts emitted React warnings about a spread `key` prop and `dataKey` DOM prop |
| Browser console after correction | PASS | Fresh Vintage Inspector render produced no Recharts warnings |

Screenshots:

- [Overview](./manual-overview.png)
- [Accuracy Dashboard](./manual-accuracy.png)
- [Vintage Inspector](./manual-vintages.png)
- [Data Provenance](./manual-provenance.png)

The console warnings occurred while rendering the Recharts Vintage Inspector chart. They did
not prevent rendering or alter values. They were corrected after this manual run by replacing
the custom dot prop spread with explicit SVG attributes and an explicit dot key. The
backend-unavailable test also intentionally produced proxy 500 messages while resilience
behavior was being tested; those were expected test events, not startup failures.

## 11. Backend warnings/errors

- Normal live startup logs showed successful FUELHH and WINDFOR retrieval and analysis.
- No startup exceptions, parse errors, duplicate warnings, or fallback warnings were observed.
- Expected proxy errors occurred only while the backend was intentionally stopped.
- Existing production build warning: JavaScript chunk exceeds the 500 kB advisory threshold.

## 12. Fixes applied during this phase

The quality-correction pass changed only the Vintage Inspector chart dot rendering and
methodology wording. The chart no longer spreads Recharts props onto a native SVG element.
The existing audit correction removing implicit fixture fallback was verified by live startup,
resilience testing, and the backend regression suite.

The D-1 09:00 UTC boundary remains unchanged. Frontend and documentation text now identifies it
as a configurable project evaluation policy rather than an official or universal market deadline.

The metadata API rationale was also corrected to describe D-1 09:00 UTC strictly as the
configurable project evaluation policy. Unsupported exchange-specific closing-time claims were
removed, and a backend regression test now guards against their return.

## 13. Fresh validation after corrections

The following checks were executed after the corrections:

```text
cd frontend && npm test                         # 8 passed across 3 files
cd backend && ../.venv/bin/py.test -q           # 59 passed
cd backend && ../.venv/bin/ruff check app tests # All checks passed
cd frontend && npx tsc --noEmit                 # Passed
cd frontend && npm run build                    # Passed; existing chunk-size warning only
```

Additional local metadata verification:

```text
curl http://127.0.0.1:8000/api/metadata
# data_mode=live; rationale contains the configurable project-policy wording
# and excludes EPEX SPOT, Nord Pool, and analyst-finalisation claims
```

The earlier browser screenshots and manual API checks remain valid for data behavior. A fresh
browser console check was performed by opening a fresh page and visiting the Vintage Inspector.
The `dataKey` DOM warning and spread-key warning were removed; Recharts then reported no
Vintage Inspector rendering warnings. Docker remains blocked because it is not installed.

The bundle-size warning was reviewed. The production JavaScript chunk is approximately 664 kB
minified, and the warning is advisory. Code splitting or dependency changes would be
disproportionate to this narrowly scoped correction, so no bundle optimization was made.

After the metadata correction, Docker rebuild/restart and container HTTP checks were blocked in
this execution environment because the Docker CLI is unavailable. The corrected metadata was
verified against the local FastAPI service instead; it contains the project-policy wording and
no EPEX SPOT, Nord Pool, or analyst-finalisation claims.

## 14. Automated tests rerun after testing

```text
cd frontend && npm test                         # 8 passed across 3 files
cd backend && ../.venv/bin/py.test -q           # 59 passed
cd backend && ../.venv/bin/ruff check app tests # All checks passed
cd frontend && npm run build                    # Passed; existing chunk-size warning only
```

## 15. Final assessment

The application is **ready for deployment testing**, with the pre-correction Docker runtime
verification supplied by the user and the post-correction Docker rebuild still pending in this
execution environment:

1. Re-run Docker Compose build, restart, HTTP, metadata, and UI checks after this metadata
   correction on the Docker-enabled macOS host.
2. Browser-level E2E coverage and a separate loading-race test remain optional follow-up work.

Live data integrity, analytical values, no-lookahead selection, cross-page consistency,
resilience behavior, and the three main application sections all passed their executed tests.
