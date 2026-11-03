# Data Validation

## Automated validation

Backend tests cover:

- FUELHH and WINDFOR parsing and normalization.
- UTC timestamp and settlement-period alignment.
- Cutoff boundaries before, exactly at, and after D-1 09:00 UTC.
- Latest eligible vintage selection and duplicate publication handling.
- Missing values, valid zero values, and near-zero actuals.
- Shared matched samples and metric consistency.
- Explicit live failure mode with no implicit fixture fallback.
- Concurrent fetch, retry exhaustion, cache reuse, forced reload, and initialization locking.
- Accuracy, vintage, and provenance API responses.

Frontend tests cover:

- Accuracy, vintage, and provenance page rendering.
- Loading, empty, error, and partial-data states.
- API client URL normalization and all analysis endpoint paths.

## Live January 2026 evidence

The validated live run used fixture mode disabled and retrieved:

| Check | Result |
|---|---:|
| FUELHH WIND records | 1,488 |
| WINDFOR records | 19,856 |
| Expected intervals | 1,488 |
| Matched intervals | 1,488 |
| Coverage | 100.0% |
| Post-cutoff selections | 0 |

Reported metrics are recorded in [JANUARY_2026_DATA_VALIDATION.md](JANUARY_2026_DATA_VALIDATION.md).

## Commands

```bash
cd backend
python -m pytest -q
ruff check app tests main.py

cd ../frontend
npm test
npm exec tsc -- --noEmit
npm run build
```

Docker commands require a Docker-capable environment and should be run using the sequence in
[DEPLOYMENT.md](DEPLOYMENT.md).

## Interpretation limits

The live counts and metrics describe the documented retrieval run. They are not a guarantee
that a future Elexon response, serverless instance, or public deployment will return identical
values. Duplicate/missing-source behavior is primarily verified by deterministic tests because
the documented live January response contained no duplicate or missing observations.
