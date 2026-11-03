# January 2026 Data Validation Report

## Retrieval scope

Validation used direct calls to the public Elexon BMRS API with fixture mode disabled. The
retrieval was performed on **2026-11-02** at approximately **12:28 UTC**.

| Dataset | Endpoint | Query | Retrieved |
|---|---|---|---:|
| FUELHH | `/datasets/FUELHH/stream` | `settlementDateFrom=2026-01-01`, `settlementDateTo=2026-01-31`, `fuelType=WIND` | 1,488 |
| WINDFOR | `/datasets/WINDFOR/stream` | `publishDateTimeFrom=2025-12-29T00:00:00Z`, `publishDateTimeTo=2026-02-01T00:00:00Z` | 19,856 |

The direct retrieval completed without API errors, parse failures, or unexpected response
formats. The live analysis was run with the existing selector and analyzer, not local fixtures.

## Integrity results

| Measure | Verified value |
|---|---:|
| Expected January delivery intervals | 1,488 |
| FUELHH records | 1,488 |
| Unique FUELHH intervals | 1,488 |
| FUELHH duplicate records | 0 |
| FUELHH missing generation values | 0 |
| WINDFOR records in query window | 19,856 |
| Unique WINDFOR delivery/publication keys | 19,856 |
| WINDFOR duplicate publication keys | 0 |
| WINDFOR missing generation values | 0 |
| Unique WINDFOR target intervals in January | 744 |
| Selected forecast intervals | 1,488 |
| Matched forecast/actual intervals | 1,488 |
| Missing actual intervals | 0 |
| Missing forecast intervals | 0 |
| Intervals excluded from metrics | 0 |
| Coverage | 100.0% |
| Selected forecasts after cutoff | 0 |

WINDFOR contains 744 unique January target intervals because the source data is hourly for
these observations. The established selector's hourly fallback maps each hourly forecast to
the corresponding half-hour settlement interval, yielding 1,488 evaluated forecast intervals.

## Metric result from live data

- MAE: **2,145.17 MW**
- RMSE: **2,615.81 MW**
- MBE: **1,851.90 MW**
- Median absolute error: **1,795.50 MW**
- Maximum absolute error: **6,894.00 MW**
- Matched sample: **1,488 / 1,488**

## Cross-feature and no-lookahead checks

Automated tests verify that Accuracy, Vintage Inspector, and Data Provenance use the same
selected forecast and actual values, preserve `forecast - actual` error semantics, and exclude
intervals with missing observations from accuracy metrics. Existing and new selector tests cover
before-cutoff, exactly-at-cutoff, after-cutoff, multiple eligible vintages, no eligible vintage,
duplicate publications, and UTC interval mapping.

## Limitations

- Retrieval timestamps are recorded for this validation run; the application cache remains
  in-memory and does not persist raw extracts.
- No duplicate or missing source observations were present in this live January response, so
  duplicate/missing behavior is verified through deterministic unit and cross-feature tests,
  not observed live incidents.
- The WINDFOR query includes the configured pre/post evaluation window so publication vintages
  around each D-1 cutoff are available. It includes records outside January delivery dates,
  which are excluded from the January selector results.
