import React, { useEffect, useMemo, useState } from 'react';
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { AlertCircle, Info } from 'lucide-react';
import { apiClient } from '../api/client';
import type { AccuracyResponse, SeriesResponse } from '../api/types';
import { ErrorAlert } from '../components/ErrorAlert';
import { KPICard } from '../components/KPICard';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { formatMW, formatUTC } from '../utils/format';

const chartStyle = {
  backgroundColor: '#0f172a',
  borderColor: '#334155',
  borderRadius: '0.75rem',
  fontSize: '12px',
};

export const AccuracyPage: React.FC = () => {
  const [accuracy, setAccuracy] = useState<AccuracyResponse | null>(null);
  const [series, setSeries] = useState<SeriesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [accuracyData, seriesData] = await Promise.all([
        apiClient.getAccuracy(),
        apiClient.getSeries(),
      ]);
      setAccuracy(accuracyData);
      setSeries(seriesData);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Failed to load accuracy data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const chartData = useMemo(
    () =>
      (series?.series ?? [])
        .filter((point) => point.actual_mw !== null || point.forecast_mw !== null)
        .map((point) => ({
          ...point,
          displayTime: point.start_time.replace('T', ' ').substring(5, 16),
          absoluteError: point.error_mw === null ? null : Math.abs(point.error_mw),
        })),
    [series],
  );

  if (loading) return <LoadingSkeleton rows={8} />;
  if (error) return <ErrorAlert message={error} onRetry={fetchData} />;
  if (!accuracy) return <ErrorAlert message="No accuracy response was returned." onRetry={fetchData} />;

  const metrics = accuracy.metrics;
  const hasMatchedData = metrics.sample_size > 0;

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h2 className="text-xl font-bold text-slate-100">Forecast Accuracy Dashboard</h2>
            <p className="mt-1 text-sm text-slate-400">
              January 2026 eligible day-ahead forecasts versus national wind outturn.
              All metrics use the same matched half-hourly intervals.
            </p>
          </div>
          <span className="rounded-md border border-slate-700 bg-slate-950 px-2.5 py-1 text-xs text-slate-400">
            {metrics.unit} · UTC · D-1 cutoff
          </span>
        </div>
        {accuracy.warnings.map((warning) => (
          <div key={warning} className="mt-4 flex items-start gap-2 text-xs text-amber-300">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{warning}</span>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KPICard label="Mean Absolute Error" value={metrics.mae_mw} unit="MW" highlight
          description="Typical forecast deviation, ignoring direction." />
        <KPICard label="Root Mean Squared Error" value={metrics.rmse_mw} unit="MW"
          description="Penalises large forecast errors more heavily than MAE." />
        <KPICard label="Mean Bias Error" value={metrics.mbe_mw} unit="MW"
          trend={metrics.mbe_mw === null ? 'neutral' : metrics.mbe_mw > 0 ? 'positive' : 'negative'}
          description="Signed forecast minus actual. Positive means overforecast; negative means underforecast." />
        <KPICard label="Matched Coverage" value={metrics.coverage_pct} unit="%"
          description={`${metrics.sample_size} valid matched intervals out of ${metrics.total_intervals}.`} />
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <KPICard label="Median Absolute Error" value={metrics.median_abs_error_mw} unit="MW"
          description="Middle absolute error; less sensitive to outliers." />
        <KPICard label="Maximum Absolute Error" value={metrics.max_abs_error_mw} unit="MW"
          description="Largest absolute error among valid matched intervals." />
      </div>

      {!hasMatchedData ? (
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-8 text-center">
          <Info className="mx-auto h-8 w-8 text-slate-500" />
          <h3 className="mt-3 text-sm font-semibold text-slate-200">No matched intervals</h3>
          <p className="mt-1 text-xs text-slate-400">
            Charts are unavailable until both a forecast and actual value exist for an interval.
          </p>
        </div>
      ) : (
        <>
          <ChartCard title="Actual versus eligible forecast" subtitle="Generation in MW across all returned settlement intervals.">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                <XAxis dataKey="displayTime" stroke="#64748b" fontSize={11} interval="preserveStartEnd" />
                <YAxis stroke="#64748b" fontSize={11} tickFormatter={(value) => `${(value / 1000).toFixed(0)}k`} />
                <Tooltip contentStyle={chartStyle}
                  labelFormatter={(_, items) => items?.[0]?.payload ? formatUTC(items[0].payload.start_time) : ''} />
                <Legend />
                <Line type="monotone" dataKey="actual_mw" name="Actual Outturn" stroke="#34d399" dot={false} connectNulls />
                <Line type="monotone" dataKey="forecast_mw" name="Selected Forecast" stroke="#22d3ee" dot={false} connectNulls />
              </ComposedChart>
            </ResponsiveContainer>
          </ChartCard>

          <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
            <ChartCard title="Absolute error over time" subtitle="Absolute forecast deviation for each interval, in MW.">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                  <XAxis dataKey="displayTime" stroke="#64748b" fontSize={11} interval="preserveStartEnd" />
                  <YAxis stroke="#64748b" fontSize={11} />
                  <Tooltip contentStyle={chartStyle} formatter={(value: number) => [`${formatMW(value)} MW`, 'Absolute error']} />
                  <Line type="monotone" dataKey="absoluteError" name="Absolute error" stroke="#f59e0b" dot={false} connectNulls />
                </ComposedChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard title="Forecast error distribution" subtitle="Signed error bins; positive values indicate overforecasting.">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={accuracy.error_distribution} margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                  <XAxis dataKey="bin_start" stroke="#64748b" fontSize={11} tickFormatter={(value) => formatMW(value)} />
                  <YAxis stroke="#64748b" fontSize={11} allowDecimals={false} />
                  <Tooltip contentStyle={chartStyle}
                    formatter={(value: number) => [value, 'Intervals']}
                    labelFormatter={(value) => `${formatMW(Number(value))} MW bin start`} />
                  <Bar dataKey="count" name="Intervals" fill="#a78bfa" />
                </ComposedChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>
        </>
      )}

      <div className="rounded-xl border border-slate-800 bg-slate-900 p-5 text-xs leading-relaxed text-slate-400">
        <strong className="text-slate-200">How to read these metrics:</strong> MAE describes typical
        error size, RMSE highlights large misses, and median absolute error describes the middle
        interval. MBE is signed as <span className="text-cyan-300">forecast minus actual</span>:
        positive values mean the forecast was above outturn, while negative values mean it was below
        outturn. Missing forecast or actual values are excluded from every metric.
      </div>
    </div>
  );
};

const ChartCard: React.FC<{ title: string; subtitle: string; children: React.ReactNode }> = ({
  title,
  subtitle,
  children,
}) => (
  <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-xl">
    <h3 className="text-base font-bold text-slate-100">{title}</h3>
    <p className="mt-1 text-xs text-slate-400">{subtitle}</p>
    <div className="mt-4 h-[340px] w-full">{children}</div>
  </section>
);
