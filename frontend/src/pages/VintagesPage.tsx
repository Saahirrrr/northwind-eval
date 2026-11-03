import React, { useEffect, useMemo, useState } from 'react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { AlertCircle, ChevronLeft, ChevronRight, Clock3 } from 'lucide-react';
import { apiClient } from '../api/client';
import type { AlternativeVintage, VintagesResponse } from '../api/types';
import { ErrorAlert } from '../components/ErrorAlert';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { formatMW, formatUTC } from '../utils/format';

const chartStyle = {
  backgroundColor: '#0f172a',
  borderColor: '#334155',
  borderRadius: '0.75rem',
  fontSize: '12px',
};

export const VintagesPage: React.FC = () => {
  const [date, setDate] = useState('2026-01-15');
  const [page, setPage] = useState(1);
  const [data, setData] = useState<VintagesResponse | null>(null);
  const [selectedInterval, setSelectedInterval] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchVintages = async (requestedDate = date, requestedPage = page) => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.getVintages(requestedDate, requestedPage, 48);
      setData(response);
      setSelectedInterval((current) =>
        response.records.some((record) => record.start_time === current)
          ? current
          : response.records[0]?.start_time ?? null,
      );
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Failed to load forecast vintages');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchVintages();
  }, []);

  const handleDateChange = (value: string) => {
    setDate(value);
    setPage(1);
    fetchVintages(value, 1);
  };

  const record = data?.records.find((item) => item.start_time === selectedInterval);
  const vintages = record?.vintages ?? record?.alternative_vintages ?? [];
  const chartData = useMemo(
    () =>
      vintages.map((vintage) => ({
        ...vintage,
        label: vintage.publish_time.replace('T', ' ').substring(5, 16),
      })),
    [vintages],
  );
  const cutoff = record?.cutoff_time;

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="text-xl font-bold text-slate-100">Forecast Vintage Inspector</h2>
            <p className="mt-1 max-w-3xl text-sm text-slate-400">
              Inspect every available WINDFOR publication for a delivery interval and verify the
              no-lookahead selection used in this project evaluation.
            </p>
          </div>
          <label className="text-xs text-slate-400">
            Delivery date (UTC)
            <input
              type="date"
              min="2026-01-01"
              max="2026-01-31"
              value={date}
              onChange={(event) => handleDateChange(event.target.value)}
              className="mt-1 block rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-slate-200"
            />
          </label>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-3 text-xs">
          <span className="flex items-center gap-1.5 rounded-md border border-cyan-500/30 bg-cyan-500/10 px-2.5 py-1 text-cyan-300">
            <Clock3 className="h-3.5 w-3.5" /> {data?.cutoff_policy ?? 'D-1 at 09:00 UTC'}
          </span>
          <span className="text-slate-400">All timestamps are UTC. Forecast values are MW.</span>
          {data?.data_mode === 'fixture' && (
            <span className="flex items-center gap-1 text-amber-300">
              <AlertCircle className="h-3.5 w-3.5" /> Local verified fixture data
            </span>
          )}
        </div>
      </div>

      {loading && <LoadingSkeleton rows={8} />}
      {error && <ErrorAlert message={error} onRetry={() => fetchVintages()} />}
      {!loading && !error && data && data.records.length === 0 && (
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-8 text-center text-sm text-slate-400">
          No delivery intervals were returned for {date}.
        </div>
      )}
      {!loading && !error && data && data.records.length > 0 && record && (
        <>
          <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-bold text-slate-100">
                  Delivery interval: {formatUTC(record.start_time)} · SP {record.settlement_period}
                </h3>
                <p className="mt-1 text-xs text-slate-400">
                  Actual: {record.actual_mw === null ? 'not available' : `${formatMW(record.actual_mw)} MW`}
                  {' · '}Selected forecast: {record.forecast_mw === null ? 'none' : `${formatMW(record.forecast_mw)} MW`}
                </p>
              </div>
              <p className="max-w-xl text-right text-xs text-cyan-300">{record.selection_reason}</p>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <h3 className="text-base font-bold text-slate-100">Forecast values by publication vintage</h3>
            <p className="mt-1 text-xs text-slate-400">
              The vertical marker is this evaluation policy's configurable D-1 09:00 UTC cutoff.
              The selected point is the latest eligible publication at or before that marker.
            </p>
            <div className="mt-4 h-[320px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                  <XAxis dataKey="label" stroke="#64748b" fontSize={11} />
                  <YAxis stroke="#64748b" fontSize={11} />
                  <Tooltip
                    contentStyle={chartStyle}
                    formatter={(value) => [
                      value == null ? '—' : `${formatMW(Number(value))} MW`,
                      'Forecast',
                    ]}
                  />
                  <Line
                    type="monotone"
                    dataKey="generation_mw"
                    stroke="#22d3ee"
                    dot={({ cx, cy, index }) => {
                      const vintage = chartData[index];
                      return (
                        <circle
                          key={vintage?.publish_time ?? index}
                          cx={cx}
                          cy={cy}
                          r={vintage?.selected ? 6 : 3}
                          fill={vintage?.selected ? '#34d399' : '#22d3ee'}
                        />
                      );
                    }}
                  />
                  {cutoff && (
                    <ReferenceLine
                      x={cutoff.replace('T', ' ').substring(5, 16)}
                      stroke="#f59e0b"
                      strokeDasharray="5 5"
                      label={{ value: 'Cutoff', fill: '#fbbf24', fontSize: 11 }}
                    />
                  )}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900">
            <table className="min-w-full text-left text-xs">
              <thead className="border-b border-slate-800 text-slate-400">
                <tr>
                  <th className="px-4 py-3">Publication (UTC)</th>
                  <th className="px-4 py-3">Forecast</th>
                  <th className="px-4 py-3">Actual</th>
                  <th className="px-4 py-3">Error</th>
                  <th className="px-4 py-3">Status / rationale</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {vintages.map((vintage) => (
                  <VintageRow key={`${vintage.publish_time}-${vintage.generation_mw}`} vintage={vintage} actual={record.actual_mw} />
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-900 px-4 py-3 text-xs">
            <span className="text-slate-400">
              Showing delivery intervals {(data.page - 1) * data.page_size + 1}–{Math.min(data.page * data.page_size, data.total_records)} of {data.total_records}
            </span>
            <div className="flex gap-2">
              <button aria-label="Previous page" disabled={data.page <= 1} onClick={() => { setPage(data.page - 1); fetchVintages(date, data.page - 1); }} className="rounded-md border border-slate-700 p-2 text-slate-300 disabled:opacity-40"><ChevronLeft className="h-4 w-4" /></button>
              <button aria-label="Next page" disabled={data.page * data.page_size >= data.total_records} onClick={() => { setPage(data.page + 1); fetchVintages(date, data.page + 1); }} className="rounded-md border border-slate-700 p-2 text-slate-300 disabled:opacity-40"><ChevronRight className="h-4 w-4" /></button>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {data.records.map((item) => (
              <button key={item.start_time} onClick={() => setSelectedInterval(item.start_time)}
                className={`rounded-md border px-2 py-1 text-xs ${item.start_time === selectedInterval ? 'border-cyan-400 bg-cyan-500/10 text-cyan-300' : 'border-slate-700 text-slate-400'}`}>
                SP {item.settlement_period}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
};

const VintageRow: React.FC<{ vintage: AlternativeVintage; actual: number | null }> = ({ vintage, actual }) => {
  const error = vintage.generation_mw === null || actual === null ? null : vintage.generation_mw - actual;
  const status = vintage.selected ? 'Selected' : vintage.eligible ? 'Eligible, not selected' : 'After cutoff';
  const statusClass = vintage.selected ? 'text-emerald-300' : vintage.eligible ? 'text-cyan-300' : 'text-rose-300';
  return (
    <tr className={vintage.selected ? 'bg-emerald-500/5' : ''}>
      <td className="px-4 py-3 font-mono text-slate-300">{formatUTC(vintage.publish_time)}</td>
      <td className="px-4 py-3 text-slate-200">{vintage.generation_mw === null ? '—' : `${formatMW(vintage.generation_mw)} MW`}</td>
      <td className="px-4 py-3 text-slate-300">{actual === null ? 'Not available' : `${formatMW(actual)} MW`}</td>
      <td className="px-4 py-3 text-slate-300">{error === null ? '—' : `${formatMW(error)} MW`}</td>
      <td className={`max-w-md px-4 py-3 ${statusClass}`}><strong>{status}</strong><br /><span className="text-slate-400">{vintage.selection_reason}</span></td>
    </tr>
  );
};
