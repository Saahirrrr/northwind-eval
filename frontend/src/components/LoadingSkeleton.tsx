import React from 'react';

export const LoadingSkeleton: React.FC<{ rows?: number }> = ({ rows = 4 }) => {
  return (
    <div className="space-y-4 animate-pulse" role="status" aria-label="Loading">
      <span className="sr-only">Loading…</span>
      <div className="h-8 bg-slate-800 rounded-lg w-1/4"></div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-28 bg-slate-900 border border-slate-800 rounded-xl p-4">
            <div className="h-4 bg-slate-800 rounded w-1/2 mb-3"></div>
            <div className="h-8 bg-slate-800 rounded w-3/4"></div>
          </div>
        ))}
      </div>
      <div className="h-72 bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="h-10 bg-slate-800/60 rounded"></div>
        ))}
      </div>
    </div>
  );
};
