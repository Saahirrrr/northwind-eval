import '@testing-library/jest-dom/vitest';
import React from 'react';
import { vi } from 'vitest';

vi.mock('recharts', () => {
  const Chart = ({ data, children }: { data?: unknown[]; children?: React.ReactNode }) => (
    <div data-testid="mock-chart" data-chart-data={JSON.stringify(data ?? [])}>{children}</div>
  );
  const Child = ({ children }: { children?: React.ReactNode }) => <>{children}</>;
  return {
    ResponsiveContainer: Chart,
    ComposedChart: Chart,
    LineChart: Chart,
    BarChart: Chart,
    Line: Child,
    Bar: Child,
    Area: Child,
    XAxis: Child,
    YAxis: Child,
    Tooltip: Child,
    Legend: Child,
    CartesianGrid: Child,
    ReferenceLine: Child,
  };
});

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: () => ({
    matches: false,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});
