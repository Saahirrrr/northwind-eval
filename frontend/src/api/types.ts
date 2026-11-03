export interface OverviewKPI {
  label: string;
  value: number | string | null;
  unit: string;
  description: string;
}

export interface CoverageInfo {
  matched: number;
  total: number;
  percentage: number | null;
}

export interface OverviewResponse {
  evaluation_period_start: string;
  evaluation_period_end: string;
  cutoff_policy: string;
  data_freshness: string | null;
  data_mode: 'live' | 'fixture' | 'error' | string;
  kpis: OverviewKPI[];
  coverage: CoverageInfo;
  warnings: string[];
}

export interface SeriesPoint {
  start_time: string;
  settlement_date: string;
  settlement_period: number;
  actual_mw: number | null;
  forecast_mw: number | null;
  error_mw: number | null;
  publish_time: string | null;
}

export interface SeriesResponse {
  series: SeriesPoint[];
  total_points: number;
  matched_points: number;
  unit: string;
  timezone: string;
  data_mode: string;
}

export interface AccuracyMetrics {
  mae_mw: number | null;
  rmse_mw: number | null;
  mbe_mw: number | null;
  max_abs_error_mw: number | null;
  median_abs_error_mw: number | null;
  sample_size: number;
  total_intervals: number;
  coverage_pct: number | null;
  unit: string;
  bias_convention: string;
}

export interface DailyAccuracy {
  date: string;
  mae_mw: number | null;
  mbe_mw: number | null;
  rmse_mw: number | null;
  sample_size: number;
}

export interface HourlyAccuracy {
  hour: number;
  mae_mw: number | null;
  mbe_mw: number | null;
  sample_size: number;
}

export interface ErrorBucket {
  bin_start: number;
  bin_end: number;
  count: number;
}

export interface AccuracyResponse {
  metrics: AccuracyMetrics;
  daily_accuracy: DailyAccuracy[];
  hourly_accuracy: HourlyAccuracy[];
  error_distribution: ErrorBucket[];
  data_mode: string;
  warnings: string[];
}

export interface AlternativeVintage {
  publish_time: string;
  generation_mw: number | null;
  eligible: boolean;
  selected?: boolean;
  selection_reason?: string;
  duplicate_publication?: boolean;
}

export interface VintageRecord {
  start_time: string;
  settlement_date: string;
  settlement_period: number;
  actual_mw: number | null;
  forecast_mw: number | null;
  publish_time: string;
  cutoff_time: string;
  forecast_age_hours: number | null;
  error_mw: number | null;
  has_actual: boolean;
  has_forecast: boolean;
  eligible: boolean;
  alternative_vintages: AlternativeVintage[];
  vintages: AlternativeVintage[];
  selection_reason: string | null;
}

export interface VintagesResponse {
  records: VintageRecord[];
  total_records: number;
  page: number;
  page_size: number;
  data_mode: string;
  cutoff_policy: string;
}

export interface DataSourceMetadata {
  name: string;
  description: string;
  provider: string;
  url: string;
  filter?: string;
  unit: string;
}

export interface MetadataResponse {
  app_name: string;
  version: string;
  data_sources: DataSourceMetadata[];
  evaluation_period: {
    start: string;
    end: string;
  };
  cutoff_policy: {
    description: string;
    days_before_delivery: number;
    hour_utc: number;
    minutes_utc: number;
    rationale: string;
  };
  units: {
    generation: string;
    time_resolution: string;
    timezone: string;
  };
  last_data_fetch: string | null;
  data_mode: string;
}

export interface ProvenanceRecord {
  source_id: string;
  dataset: 'FUELHH' | 'WINDFOR' | string;
  delivery_interval: string;
  settlement_date: string;
  settlement_period: number;
  publication_time: string | null;
  cutoff_time: string;
  raw_generation_mw: number | null;
  normalized_generation_mw: number | null;
  actual_generation_mw: number | null;
  forecast_error_mw: number | null;
  eligible: boolean | null;
  selected: boolean | null;
  matching_status: string;
  duplicate: boolean;
  missing: boolean;
  transformation_explanation: string;
  raw_record: Record<string, unknown>;
}

export interface ProvenanceResponse {
  records: ProvenanceRecord[];
  total_records: number;
  page: number;
  page_size: number;
  data_mode: string;
  cutoff_policy: string;
  timezone: string;
}
