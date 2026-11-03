import React, { useEffect, useState } from 'react';
import { ChevronLeft, ChevronRight, Database, Eye, FileWarning } from 'lucide-react';
import { apiClient } from '../api/client';
import type { ProvenanceRecord, ProvenanceResponse } from '../api/types';
import { ErrorAlert } from '../components/ErrorAlert';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { formatMW, formatUTC } from '../utils/format';

export const ProvenancePage: React.FC = () => {
  const [date, setDate] = useState('2026-01-15');
  const [period, setPeriod] = useState('');
  const [page, setPage] = useState(1);
  const [data, setData] = useState<ProvenanceResponse | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async (requestedDate = date, requestedPeriod = period, requestedPage = page) => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.getProvenance(
        requestedDate,
        requestedPeriod ? Number(requestedPeriod) : undefined,
        undefined,
        requestedPage,
        50,
      );
      setData(response);
      setExpanded(null);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Failed to load provenance data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const applyFilter = (event: React.FormEvent) => {
    event.preventDefault();
    setPage(1);
    fetchData(date, period, 1);
  };

  return (
    <div className="space-y-6">
      <header className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
        <h2 className="text-xl font-bold text-slate-100">Data Provenance</h2>
        <p className="mt-1 max-w-4xl text-sm text-slate-400">
          Trace normalized analysis values back to the validated FUELHH and WINDFOR source
          records. Missing records remain explicit, and no source identifiers are invented.
        </p>
        <form onSubmit={applyFilter} className="mt-5 flex flex-wrap items-end gap-3">
          <label className="text-xs text-slate-400">
            Delivery date (UTC)
            <input type="date" min="2026-01-01" max="2026-01-31" value={date}
              onChange={(event) => setDate(event.target.value)}
              className="mt-1 block rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-slate-200" />
          </label>
          <label className="text-xs text-slate-400">
            Settlement period
            <input type="number" min="1" max="48" placeholder="All" value={period}
              onChange={(event) => setPeriod(event.target.value)}
              className="mt-1 block w-28 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-slate-200" />
          </label>
          <button type="submit" className="rounded-lg bg-cyan-600 px-4 py-2 text-xs font-semibold text-white hover:bg-cyan-500">
            Apply filters
          </button>
        </form>
        <div className="mt-4 flex flex-wrap gap-3 text-xs text-slate-400">
          <span className="rounded-md border border-cyan-500/30 bg-cyan-500/10 px-2.5 py-1 text-cyan-300">
            {data?.cutoff_policy ?? 'D-1 at 09:00 UTC'}
          </span>
          <span>Source values and normalized values are shown separately · {data?.timezone ?? 'UTC'}</span>
          {data?.data_mode === 'fixture' && <span className="text-amber-300">Verified local fixture data</span>}
        </div>
      </header>

      {loading && <LoadingSkeleton rows={8} />}
      {error && <ErrorAlert message={error} onRetry={() => fetchData()} />}
      {!loading && !error && data && data.records.length === 0 && (
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-8 text-center text-sm text-slate-400">
          No provenance records match the selected filters.
        </div>
      )}
      {!loading && !error && data && data.records.length > 0 && (
        <>
          <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900">
            <table className="min-w-[1100px] w-full text-left text-xs">
              <thead className="border-b border-slate-800 text-slate-400">
                <tr>
                  <th className="px-4 py-3">Dataset / source</th>
                  <th className="px-4 py-3">Delivery interval (UTC)</th>
                  <th className="px-4 py-3">Published / cutoff</th>
                  <th className="px-4 py-3">Generation</th>
                  <th className="px-4 py-3">Match / selection</th>
                  <th className="px-4 py-3">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {data.records.map((record) => (
                  <ProvenanceRow key={`${record.source_id}-${record.delivery_interval}`} record={record}
                    open={expanded === record.source_id} onToggle={() => setExpanded(
                      expanded === record.source_id ? null : record.source_id,
                    )} />
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-900 px-4 py-3 text-xs">
            <span className="text-slate-400">
              Showing {(data.page - 1) * data.page_size + 1}–{Math.min(data.page * data.page_size, data.total_records)} of {data.total_records} source records
            </span>
            <div className="flex gap-2">
              <button aria-label="Previous page" disabled={data.page <= 1} onClick={() => { setPage(data.page - 1); fetchData(date, period, data.page - 1); }}
                className="rounded-md border border-slate-700 p-2 text-slate-300 disabled:opacity-40"><ChevronLeft className="h-4 w-4" /></button>
              <button aria-label="Next page" disabled={data.page * data.page_size >= data.total_records} onClick={() => { setPage(data.page + 1); fetchData(date, period, data.page + 1); }}
                className="rounded-md border border-slate-700 p-2 text-slate-300 disabled:opacity-40"><ChevronRight className="h-4 w-4" /></button>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

const ProvenanceRow: React.FC<{
  record: ProvenanceRecord;
  open: boolean;
  onToggle: () => void;
}> = ({ record, open, onToggle }) => (
  <>
    <tr className={record.selected ? 'bg-emerald-500/5' : ''}>
      <td className="px-4 py-3">
        <span className={`inline-flex items-center gap-1 rounded px-2 py-1 font-semibold ${
          record.dataset === 'FUELHH' ? 'bg-amber-500/10 text-amber-300' : 'bg-cyan-500/10 text-cyan-300'
        }`}><Database className="h-3 w-3" />{record.dataset}</span>
        <div className="mt-1 max-w-[190px] truncate font-mono text-[10px] text-slate-500" title={record.source_id}>{record.source_id}</div>
      </td>
      <td className="px-4 py-3 font-mono text-slate-300">{formatUTC(record.delivery_interval)}<br /><span className="text-slate-500">SP {record.settlement_period}</span></td>
      <td className="px-4 py-3 font-mono text-slate-300">{record.publication_time ? formatUTC(record.publication_time) : 'Missing'}<br /><span className="text-slate-500">cutoff {formatUTC(record.cutoff_time)}</span></td>
      <td className="px-4 py-3 text-slate-300">
        raw: {record.raw_generation_mw === null ? '—' : `${formatMW(record.raw_generation_mw)} MW`}<br />
        normalized: {record.normalized_generation_mw === null ? '—' : `${formatMW(record.normalized_generation_mw)} MW`}
        {record.forecast_error_mw !== null && <><br />error: {formatMW(record.forecast_error_mw)} MW</>}
      </td>
      <td className="px-4 py-3">
        <span className={record.missing ? 'text-rose-300' : record.selected ? 'text-emerald-300' : record.eligible === false ? 'text-rose-300' : 'text-cyan-300'}>
          {record.missing ? 'Missing source record' : record.selected ? 'Selected vintage' : record.eligible === false ? 'After cutoff' : record.eligible === true ? 'Eligible' : record.matching_status}
        </span>
        {record.duplicate && <div className="mt-1 flex items-center gap-1 text-amber-300"><FileWarning className="h-3 w-3" />Duplicate indicator</div>}
      </td>
      <td className="px-4 py-3"><button onClick={onToggle} className="flex items-center gap-1 text-cyan-300 hover:text-cyan-200"><Eye className="h-4 w-4" />{open ? 'Hide' : 'Raw record'}</button></td>
    </tr>
    {open && <tr><td colSpan={6} className="bg-slate-950 px-6 py-4">
      <p className="mb-2 text-xs text-slate-400">{record.transformation_explanation}</p>
      <pre className="max-h-48 overflow-auto rounded-lg border border-slate-800 bg-slate-900 p-3 text-[11px] text-slate-300">{JSON.stringify(record.raw_record, null, 2)}</pre>
    </td></tr>}
  </>
);
