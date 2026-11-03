import React, { useEffect, useState, useMemo } from 'react';
import { apiClient } from '../api/client';
import type { SeriesResponse } from '../api/types';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { ErrorAlert } from '../components/ErrorAlert';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from 'recharts';
import { formatMW, formatUTC } from '../utils/format';
import { Filter, RotateCcw, Calendar } from 'lucide-react';

export const SeriesPage: React.FC = () => {
  const [data, setData] = useState<SeriesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [dateFrom, setDateFrom] = useState<string>('2026-01-01');
  const [dateTo, setDateTo] = useState<string>('2026-01-07');

  const fetchSeries = async (from?: string, to?: string) => {
    try {
      setLoading(true);
      setError(null);
      const res = await apiClient.getSeries(from, to);
      setData(res);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Failed to load time-series data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSeries(dateFrom, dateTo);
  }, []);

  const handleApplyFilter = (e: React.FormEvent) => {
    e.preventDefault();
    fetchSeries(dateFrom, dateTo);
  };

  const handleReset = () => {
    setDateFrom('2026-01-01');
    setDateTo('2026-01-07');
    fetchSeries('2026-01-01', '2026-01-07');
  };

  // Formatted chart points
  const chartData = useMemo(() => {
    if (!data?.series) return [];
    return data.series.map((item) => ({
      ...item,
      displayTime: item.start_time.replace('T', ' ').substring(5, 16),
      // For dual area fill
      absError: item.error_mw !== null ? Math.abs(item.error_mw) : null,
    }));
  }, [data]);

  return (
    <div className="space-y-6">
      {/* Filter Toolbar */}
      <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex flex-wrap items-center justify-between gap-4">
        <form onSubmit={handleApplyFilter} className="flex flex-wrap items-center gap-3 text-xs">
          <div className="flex items-center gap-2 text-slate-300 font-semibold uppercase tracking-wider">
            <Filter className="w-4 h-4 text-cyan-400" />
            Interval Filter:
          </div>

          <div className="flex items-center gap-2">
            <label htmlFor="dateFrom" className="text-slate-400">From:</label>
            <input
              id="dateFrom"
              type="date"
              min="2026-01-01"
              max="2026-01-31"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
            />
          </div>

          <div className="flex items-center gap-2">
            <label htmlFor="dateTo" className="text-slate-400">To:</label>
            <input
              id="dateTo"
              type="date"
              min="2026-01-01"
              max="2026-01-31"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
            />
          </div>

          <button
            type="submit"
            className="px-3.5 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-medium transition-colors shadow-sm"
          >
            Apply Range
          </button>

          <button
            type="button"
            onClick={handleReset}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium transition-colors border border-slate-700"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Reset
          </button>
        </form>

        <div className="flex items-center gap-4 text-xs text-slate-400">
          <div>
            Points: <span className="font-semibold text-slate-200">{data?.matched_points ?? 0}</span> matched / {data?.total_points ?? 0} total
          </div>
          <div className="flex items-center gap-1 font-mono text-[11px] text-slate-400 bg-slate-950 px-2 py-1 rounded border border-slate-800">
            <Calendar className="w-3.5 h-3.5" />
            30-Min Resolution (MW)
          </div>
        </div>
      </div>

      {loading && <LoadingSkeleton rows={6} />}
      {error && <ErrorAlert message={error} onRetry={() => fetchSeries(dateFrom, dateTo)} />}

      {!loading && !error && data && (
        <div className="space-y-6">
          {/* Main Forecast vs Actual Chart */}
          <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-slate-100">
                  National Wind Generation: Eligible Day-Ahead Forecast vs Actual
                </h3>
                <p className="text-xs text-slate-400">
                  Half-hourly settlement periods across Great Britain. Shaded area indicates absolute forecast error.
                </p>
              </div>
              <div className="flex items-center gap-4 text-xs">
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-full bg-emerald-400"></span>
                  <span className="text-slate-300 font-medium">Actual Outturn (FUELHH)</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-full bg-cyan-400"></span>
                  <span className="text-slate-300 font-medium">Selected Forecast (WINDFOR)</span>
                </div>
              </div>
            </div>

            <div className="h-[460px] w-full pt-4">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 25 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                  <XAxis
                    dataKey="displayTime"
                    stroke="#64748b"
                    fontSize={11}
                    tickMargin={10}
                    interval="preserveStartEnd"
                  />
                  <YAxis
                    stroke="#64748b"
                    fontSize={11}
                    tickFormatter={(val) => `${(val / 1000).toFixed(0)}k`}
                    label={{
                      value: 'Generation (MW)',
                      angle: -90,
                      position: 'insideLeft',
                      fill: '#94a3b8',
                      fontSize: 12,
                      offset: 0,
                    }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0f172a',
                      borderColor: '#334155',
                      borderRadius: '0.75rem',
                      boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.5)',
                      fontSize: '12px',
                    }}
                    labelFormatter={(_, items) => {
                      if (!items || items.length === 0) return '';
                      const item = items[0]?.payload;
                      return item ? `${formatUTC(item.start_time)} (SP ${item.settlement_period})` : '';
                    }}
                    formatter={(value: any, name: string) => {
                      if (name === 'Selected Forecast') return [`${formatMW(value)} MW`, name];
                      if (name === 'Actual Outturn') return [`${formatMW(value)} MW`, name];
                      if (name === 'Abs Error') return [`${formatMW(value)} MW`, name];
                      return [value, name];
                    }}
                  />
                  <Legend verticalAlign="top" height={36} />

                  {/* Absolute Error Area Fill */}
                  <Area
                    type="monotone"
                    dataKey="absError"
                    name="Abs Error"
                    fill="#f43f5e"
                    fillOpacity={0.12}
                    stroke="none"
                  />

                  {/* Selected Forecast Line */}
                  <Line
                    type="monotone"
                    dataKey="forecast_mw"
                    name="Selected Forecast"
                    stroke="#22d3ee"
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 5, fill: '#22d3ee' }}
                  />

                  {/* Actual Wind Line */}
                  <Line
                    type="monotone"
                    dataKey="actual_mw"
                    name="Actual Outturn"
                    stroke="#34d399"
                    strokeWidth={2.5}
                    dot={false}
                    activeDot={{ r: 5, fill: '#34d399' }}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Signed Forecast Error Time Series (Over/Under forecasting) */}
          <div className="p-6 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl space-y-4">
            <div>
              <h3 className="text-base font-bold text-slate-100">
                Forecast Error Time Profile: (Forecast &minus; Actual)
              </h3>
              <p className="text-xs text-slate-400">
                Values above 0 MW indicate overforecasting (procurement shortfall risk in real time). Values below 0 MW indicate underforecasting.
              </p>
            </div>

            <div className="h-[220px] w-full pt-2">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                  <XAxis
                    dataKey="displayTime"
                    stroke="#64748b"
                    fontSize={11}
                    tickMargin={10}
                    interval="preserveStartEnd"
                  />
                  <YAxis
                    stroke="#64748b"
                    fontSize={11}
                    tickFormatter={(val) => `${val > 0 ? '+' : ''}${val}`}
                    label={{
                      value: 'Error (MW)',
                      angle: -90,
                      position: 'insideLeft',
                      fill: '#94a3b8',
                      fontSize: 12,
                      offset: 0,
                    }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0f172a',
                      borderColor: '#334155',
                      borderRadius: '0.75rem',
                      fontSize: '12px',
                    }}
                    labelFormatter={(_, items) => {
                      const item = items?.[0]?.payload;
                      return item ? `${formatUTC(item.start_time)} (SP ${item.settlement_period})` : '';
                    }}
                    formatter={(val: any) => [`${val > 0 ? '+' : ''}${formatMW(val)} MW`, 'Forecast Error']}
                  />
                  <Line
                    type="monotone"
                    dataKey="error_mw"
                    name="Error (MW)"
                    stroke="#f59e0b"
                    strokeWidth={1.8}
                    dot={false}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
