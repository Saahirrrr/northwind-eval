import React from 'react';
import { Info } from 'lucide-react';
import { formatMW } from '../utils/format';

interface KPICardProps {
  label: string;
  value: number | string | null | undefined;
  unit?: string;
  description?: string;
  trend?: 'positive' | 'negative' | 'neutral';
  highlight?: boolean;
}

export const KPICard: React.FC<KPICardProps> = ({
  label,
  value,
  unit = 'MW',
  description,
  trend,
  highlight = false,
}) => {
  const displayVal = typeof value === 'number' ? formatMW(value) : value ?? '—';

  return (
    <div
      className={`relative p-5 rounded-xl border transition-all duration-200 ${
        highlight
          ? 'bg-gradient-to-br from-slate-900 via-slate-850 to-slate-900 border-cyan-500/40 shadow-lg shadow-cyan-950/30'
          : 'bg-slate-900/80 border-slate-800 hover:border-slate-700'
      }`}
    >
      <div className="flex items-center justify-between gap-2 mb-2">
        <span className="text-xs font-semibold tracking-wider uppercase text-slate-400">
          {label}
        </span>
        {description && (
          <div className="group relative cursor-pointer">
            <Info className="w-4 h-4 text-slate-500 hover:text-slate-300 transition-colors" />
            <div className="absolute right-0 bottom-6 w-56 p-2.5 bg-slate-800 text-slate-200 text-xs rounded-lg border border-slate-700 shadow-xl opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-30">
              {description}
            </div>
          </div>
        )}
      </div>

      <div className="flex items-baseline gap-2">
        <span
          className={`text-2xl font-bold tracking-tight ${
            trend === 'positive'
              ? 'text-rose-400'
              : trend === 'negative'
              ? 'text-emerald-400'
              : highlight
              ? 'text-cyan-300'
              : 'text-slate-100'
          }`}
        >
          {displayVal}
        </span>
        {unit && <span className="text-sm font-medium text-slate-400">{unit}</span>}
      </div>

      {description && (
        <p className="mt-2 text-xs text-slate-400 line-clamp-2 leading-relaxed">
          {description}
        </p>
      )}
    </div>
  );
};
