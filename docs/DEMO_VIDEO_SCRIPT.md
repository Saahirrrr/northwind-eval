# 10-Minute Demonstration Video Script

Target duration: **9:30–10:00**. Record the customer section first, then the technical
section. Use the live deployment only if it is reachable and shows live mode; otherwise
state that the step is a local validation demonstration.

## Part A — Customer-facing walkthrough (0:00–4:45)

### 0:00–0:35 — Problem and context

**Screen:** Open the deployed frontend landing page.

**Narration:** “Gridbricks Wind Intelligence evaluates how well national wind-generation
forecasts matched observed generation in January 2026. The goal is not to place trades or
automatically procure electricity. It is to make the forecast evidence, error, and
information boundary easy to inspect.”

### 0:35–1:35 — Overview and accuracy

**Screen:** Open Overview, then Accuracy Dashboard. Point to MAE, RMSE, MBE, coverage, and
matched intervals.

**Narration:** “The dashboard reports error in megawatts. MBE is forecast minus actual, so
the positive January value indicates over-forecasting on average. All metrics use the same
valid matched sample, while missing values are excluded rather than changed to zero.”

### 1:35–2:30 — Forecast versus actual

**Screen:** Show generation comparison and absolute-error charts; hover one interval.

**Narration:** “This time series compares the selected forecast with actual generation.
The error view shows where the gap is largest and keeps the 30-minute delivery context
visible.”

### 2:30–3:25 — Vintage inspection

**Screen:** Open Forecast Vintage Inspector, choose `2026-01-15`, show selected, eligible,
and post-cutoff rows.

**Narration:** “For each delivery interval, the inspector shows available forecast
publications. The selected row is the latest publication at or before the configurable
D-1 09:00 UTC project evaluation boundary. This is an evaluation assumption, not an official
universal procurement deadline.”

### 3:25–4:15 — Provenance

**Screen:** Open Data Provenance, filter a date and settlement period, expand a raw record.

**Narration:** “Provenance connects the source payload to the normalized MW value, UTC
delivery interval, selection status, and forecast error. This makes the result auditable
instead of presenting only a final number.”

### 4:15–4:45 — Business value and limits

**Screen:** Return to Accuracy Dashboard.

**Narration:** “The evidence can inform a day-ahead review by showing forecast bias,
uncertainty, and which publication was used for comparison. It is not an automated
procurement system, a new forecasting model, or a portfolio optimizer. It is limited to
the January 2026 Elexon scope.”

## Transition (4:45–5:00)

**Screen:** Switch to a terminal or architecture slide.

**Narration:** “Next I’ll show how the data moves through the system and how the result is
validated.”

## Part B — Technical walkthrough (5:00–9:50)

### 5:00–5:55 — Architecture

**Screen:** Show the Mermaid architecture from `docs/ARCHITECTURE.md` or the repository tree.

**Narration:** “The frontend is React, TypeScript, and Vite. It calls a FastAPI backend.
The backend owns Elexon ingestion, matching, selection, analytics, and provenance. Docker
Compose uses Nginx as the local `/api` proxy; Vercel deploys the frontend and Python backend
as separate projects.”

### 5:55–6:45 — Ingestion and matching

**Screen:** Show `elexon_client.py`, `analysis_service.py`, and `DATA_METHODOLOGY.md`.

**Narration:** “FUELHH is filtered to WIND for actuals. WINDFOR supplies forecast vintages.
Settlement date and one-indexed period become UTC half-hour intervals. Timestamps are
normalized explicitly, and the observed hourly forecast shape uses the existing hourly
fallback.”

### 6:45–7:30 — Selection and metrics

**Screen:** Show selector logic and the accuracy response.

**Narration:** “Records at or before the configured cutoff are eligible, and the latest
eligible publication is selected. Post-cutoff records cannot be selected. The analyzer
builds one deduplicated matched sample, then calculates MAE, RMSE, MBE, median and maximum
absolute error, matched count, and coverage from that same sample.”

### 7:30–8:15 — Error handling and integrity

**Screen:** Show tests for retries, missing values, duplicate intervals, and failure mode.

**Narration:** “Missing values stay missing and zero remains valid. If live Elexon loading
fails with fixtures disabled, the service enters an explicit error state rather than
silently showing sample data. Concurrent initialization is guarded per process, while
separate serverless instances remain independent.”

### 8:15–9:05 — Deployment

**Screen:** Show Docker commands and Vercel project settings without exposing account data.

**Narration:** “Docker builds the two-service local deployment. Vercel uses Python 3.12 for
the backend and a root `main.py` forwarding entrypoint. The frontend receives its backend
origin at build time and the client adds `/api` exactly once. Production environment values
keep fixture mode false.”

### 9:05–9:40 — Tests and engineering decisions

**Screen:** Show terminal test output.

**Narration:** “Backend tests cover selection boundaries, metrics, retries, concurrency,
provenance, and API contracts. Frontend tests cover the three data views and API URL
normalization. Ruff, TypeScript, and the production build are also run. The design avoids
unnecessary databases and providers because the challenge scope is a bounded evaluation.”

### 9:40–9:50 — AI disclosure and close

**Screen:** Show README disclosure.

**Narration:** “AI coding tools helped inspect, implement, test, and document the project.
The source, commands, and validation evidence were reviewed locally, and no AI-generated
mock data is used in the production data flow. Thank you.”
