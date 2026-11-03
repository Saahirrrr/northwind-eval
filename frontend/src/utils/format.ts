/**
 * Utility functions for consistent formatting of power metrics,
 * percentages, timestamps, and intervals.
 */

export function formatMW(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) return '—';
  return new Intl.NumberFormat('en-GB', {
    maximumFractionDigits: 1,
    minimumFractionDigits: 0,
  }).format(val);
}

export function formatPercent(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) return '—';
  return `${val.toFixed(1)}%`;
}

export function formatSignedMW(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) return '—';
  const prefix = val > 0 ? '+' : '';
  return `${prefix}${formatMW(val)}`;
}

export function formatUTC(isoStr: string | null | undefined): string {
  if (!isoStr) return '—';
  const dt = new Date(isoStr);
  if (isNaN(dt.getTime())) return isoStr;

  // Format as YYYY-MM-DD HH:mm UTC
  const pad = (n: number) => String(n).padStart(2, '0');
  const y = dt.getUTCFullYear();
  const m = pad(dt.getUTCMonth() + 1);
  const d = pad(dt.getUTCDate());
  const h = pad(dt.getUTCHours());
  const min = pad(dt.getUTCMinutes());

  return `${y}-${m}-${d} ${h}:${min} UTC`;
}

export function formatTimeOnlyUTC(isoStr: string | null | undefined): string {
  if (!isoStr) return '—';
  const dt = new Date(isoStr);
  if (isNaN(dt.getTime())) return isoStr;
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${pad(dt.getUTCHours())}:${pad(dt.getUTCMinutes())}`;
}
