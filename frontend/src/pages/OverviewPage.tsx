import React, { useEffect, useState } from 'react';
import { apiClient } from '../api/client';
import type { OverviewResponse } from '../api/types';
import { KPICard } from '../components/KPICard';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { ErrorAlert } from '../components/ErrorAlert';
import { Calendar, ShieldAlert, CheckCircle2, TrendingUp, HelpCircle } from 'lucide-react';
import { formatPercent } from '../utils/format';

export const OverviewPage: React.FC = () => {
  const [data, setData] = useState<OverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchOverview = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await apiClient.getOverview();
      setData(res);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Failed to load overview data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOverview();
  }, []);

  if (loading) return <LoadingSkeleton rows={5} />;
  if (error) return <ErrorAlert message={error} onRetry={fetchOverview} />;
  if (!data) return null;

  return (
    <div className="space-y-6">
      {/* Top Banner / Context Header */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-850 to-slate-900 border border-slate-800 shadow-xl">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-cyan-400 text-xs font-semibold uppercase tracking-wider mb-1">
              <Calendar className="w-4 h-4" />
              Delivery Evaluation Window
            </div>
            <h2 className="text-xl font-bold text-slate-100">
              January 2026 Wholesale Wind Generation Evaluation
            </h2>
            <p className="text-sm text-slate-400 mt-1 max-w-3xl">
              Evaluating national day-ahead wind forecasts against actual outturn generation across
              Great Britain. Every evaluated interval uses strictly the latest eligible forecast published
              prior to the procurement decision cutoff, eliminating look-ahead bias.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="bg-slate-950/80 px-4 py-2.5 rounded-xl border border-slate-800">
              <span className="text-[11px] uppercase tracking-wider text-slate-400 block font-medium">
                Period Range
              </span>
              <span className="text-sm font-semibold text-slate-200">
                {data.evaluation_period_start} &rarr; {data.evaluation_period_end}
              </span>
            </div>

            <div className="bg-slate-950/80 px-4 py-2.5 rounded-xl border border-slate-800">
              <span className="text-[11px] uppercase tracking-wider text-slate-400 block font-medium">
                Data Coverage
              </span>
              <div className="flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span className="text-sm font-semibold text-emerald-300">
                  {formatPercent(data.coverage.percentage)}
                </span>
                <span className="text-xs text-slate-400">
                  ({data.coverage.matched} / {data.coverage.total})
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Warnings list if any */}
        {data.warnings && data.warnings.length > 0 && (
          <div className="mt-4 pt-4 border-t border-slate-800/80">
            {data.warnings.map((w, idx) => (
              <div key={idx} className="flex items-center gap-2 text-xs text-amber-300/90 py-0.5">
                <ShieldAlert className="w-3.5 h-3.5 shrink-0" />
                <span>{w}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* KPI Grid */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
            Primary Accuracy Key Performance Indicators
          </h3>
          <span className="text-xs text-slate-400">
            Source: Elexon BMRS WINDFOR (Day-Ahead) vs FUELHH (Actual Wind)
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.kpis.map((kpi, idx) => (
            <KPICard
              key={idx}
              label={kpi.label}
              value={kpi.value}
              unit={kpi.unit}
              description={kpi.description}
              highlight={idx === 0 || idx === 1}
            />
          ))}
        </div>
      </div>

      {/* Domain Logic Highlights & Procurement Analysis Context */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
          <div className="flex items-center gap-2 text-cyan-400 text-sm font-semibold">
            <TrendingUp className="w-4 h-4" />
            Evaluation Cutoff Methodology
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            This project uses a configurable D-1 09:00 UTC cutoff as an evaluation policy for
            comparing the information available before a defined decision point. It is not a
            universal or official UK electricity procurement deadline.
          </p>
          <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs space-y-1 font-mono text-slate-300">
            <div><span className="text-cyan-400">Active Cutoff:</span> {data.cutoff_policy}</div>
            <div><span className="text-cyan-400">Selection Policy:</span> max(publishTime) &le; Cutoff</div>
            <div><span className="text-cyan-400">Timezone:</span> UTC (= GMT in January, no DST offset)</div>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Forecasts published after 09:00 UTC on D-1 are strictly excluded from the baseline selection.
            This prevents look-ahead bias under the project policy; it does not claim to reproduce
            every market participant's information state.
          </p>
        </div>

        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
          <div className="flex items-center gap-2 text-emerald-400 text-sm font-semibold">
            <HelpCircle className="w-4 h-4" />
            Procurement Analyst Interpretation Guide
          </div>
          <ul className="text-xs text-slate-300 space-y-2 leading-relaxed">
            <li className="flex items-start gap-2">
              <span className="text-cyan-400 font-bold">&bull;</span>
              <span>
                <strong>Mean Absolute Error (MAE):</strong> Measures the typical magnitude of forecast deviation in megawatts (MW). Use this to size balancing reserve buffers.
              </span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-cyan-400 font-bold">&bull;</span>
              <span>
                <strong>Root Mean Squared Error (RMSE):</strong> Disproportionately penalises extreme forecast busts. A high RMSE relative to MAE indicates heavy-tailed error distributions.
              </span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-cyan-400 font-bold">&bull;</span>
              <span>
                <strong>Mean Bias Error (MBE):</strong> Positive values indicate systematic overforecasting (procurement under-supply risk in real time). Negative values indicate underforecasting.
              </span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
};
