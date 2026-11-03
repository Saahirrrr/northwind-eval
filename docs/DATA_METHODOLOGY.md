# Data Methodology

## Scope and sources

The evaluation covers UK national wind generation for **January 2026** using:

- Elexon BMRS `FUELHH`, filtered to `fuelType=WIND`, as actual generation.
- Elexon BMRS `WINDFOR`, as forecast vintages.

No other datasets or providers are used.

## Retrieval windows

- Actuals: settlement dates `2026-01-01` through `2026-01-31`.
- Forecast publications: `2025-12-29T00:00:00Z` through `2026-02-01T00:00:00Z`.

The wider forecast publication window allows vintages around each delivery-day cutoff to
be inspected while January delivery intervals remain the evaluation scope.

## Time normalization and matching

FUELHH settlement periods are one-indexed: SP1 begins at 00:00 UTC and SP48 begins at
23:30 UTC. The settlement date and period are converted to a UTC half-hour interval.
WINDFOR delivery and publication timestamps are normalized to UTC before association.

The observed January WINDFOR response is hourly. The existing selector's documented hourly
fallback associates each hourly forecast with the corresponding half-hour intervals.

Missing generation values remain missing. Zero generation is valid and is not converted to
missing. Duplicate observations are handled deterministically and are covered by tests.

## Forecast vintage selection

For each delivery interval:

1. Compute the configured D-1 cutoff at 09:00 UTC by default.
2. Mark records with `publish_time <= cutoff` as eligible.
3. Select the latest eligible publication.
4. Never select a publication after the cutoff.
5. Preserve alternative vintages and explicit selection/exclusion reasons for inspection.

The D-1 09:00 UTC boundary is a configurable project evaluation assumption. It is not an
official or universal UK procurement deadline and does not claim to reproduce every market
participant's information state.

## Accuracy calculations

The analyzer first creates one deduplicated matched sample containing non-null actual and
selected forecast values. All metrics are calculated from that same sample:

- MAE = mean of `abs(forecast - actual)`.
- RMSE = square root of mean squared `forecast - actual`.
- MBE = mean of `forecast - actual`; positive means over-forecasting.
- Median absolute error = median of absolute errors.
- Maximum absolute error = maximum absolute error.
- Coverage = matched valid intervals / expected intervals × 100.

Missing values are excluded from all metrics; they are never replaced with zero.

## Provenance

The provenance endpoint exposes raw validated records, normalized values, UTC timestamps,
matching status, eligibility, selection status, duplicate/missing indicators, and forecast
error where an actual exists. Deterministic SHA-256 composite IDs are used because this
integration does not receive a stable source record ID.

## Validation evidence

The documented live validation found:

- 1,488 FUELHH records.
- 19,856 WINDFOR records.
- 1,488 matched intervals.
- 100.0% coverage.
- Zero post-cutoff selections.

See [JANUARY_2026_DATA_VALIDATION.md](JANUARY_2026_DATA_VALIDATION.md) for the full evidence
and limitations.
