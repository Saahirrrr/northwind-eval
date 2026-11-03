import React from 'react';
import { Wind, Activity, TrendingUp, Clock, ShieldCheck, Database } from 'lucide-react';

export type TabType = 'overview' | 'series' | 'accuracy' | 'vintages' | 'quality';

interface LayoutProps {
  activeTab: TabType;
  onTabChange: (tab: TabType) => void;
  dataMode?: string;
  cutoffPolicy?: string;
  dataFreshness?: string | null;
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({
  activeTab,
  onTabChange,
  dataMode = 'live',
  cutoffPolicy,
  dataFreshness,
  children,
}) => {
  const tabs = [
    { id: 'overview' as TabType, label: 'Overview', icon: Activity },
    { id: 'series' as TabType, label: 'Forecast vs Actual', icon: TrendingUp },
    { id: 'accuracy' as TabType, label: 'Accuracy & Error', icon: ShieldCheck },
    { id: 'vintages' as TabType, label: 'Vintage Inspector', icon: Clock },
    { id: 'quality' as TabType, label: 'Data Provenance', icon: Database },
  ];

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col">
      {/* Top Navbar */}
      <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
              <Wind className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-bold text-slate-100 tracking-tight">
                  Gridbricks Wind Intelligence
                </h1>
                <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                  GB Wholesale
                </span>
              </div>
              <p className="text-xs text-slate-400">
                UK Day-Ahead Renewable Procurement Evaluation &bull; January 2026
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Cutoff policy badge */}
            {cutoffPolicy && (
              <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-800/80 border border-slate-700 text-xs text-slate-300">
                <Clock className="w-3.5 h-3.5 text-cyan-400" />
                <span className="font-mono text-cyan-300">{cutoffPolicy}</span>
              </div>
            )}

            {/* Data mode indicator */}
            <div className="flex items-center gap-2 px-2.5 py-1 rounded-md bg-slate-800/80 border border-slate-700 text-xs">
              <span
                className={`w-2 h-2 rounded-full ${
                  dataMode === 'live'
                    ? 'bg-emerald-400 shadow-sm shadow-emerald-400'
                    : dataMode === 'fixture'
                    ? 'bg-amber-400'
                    : 'bg-rose-400'
                }`}
              />
              <span className="capitalize text-slate-300 font-medium">
                {dataMode === 'live'
                  ? 'Elexon Live Stream'
                  : dataMode === 'fixture'
                  ? 'Historical Fixture'
                  : 'API Notice'}
              </span>
            </div>

            {/* Timezone Indicator */}
            <span className="hidden lg:inline-flex text-[11px] font-mono text-slate-400 bg-slate-900 px-2 py-1 rounded border border-slate-800">
              UTC / GMT (UK)
            </span>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex space-x-1 overflow-x-auto">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                className={`flex items-center gap-2 py-3 px-4 text-xs font-semibold border-b-2 transition-colors whitespace-nowrap ${
                  isActive
                    ? 'border-cyan-400 text-cyan-300 bg-slate-800/40'
                    : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-cyan-400' : 'text-slate-500'}`} />
                {tab.label}
              </button>
            );
          })}
        </div>
      </header>

      {/* Main Body */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {children}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-slate-950 py-4 text-xs text-slate-400">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-2">
          <div>
            Data Sources: Elexon BMRS <code className="text-slate-400">FUELHH</code> (Actual Wind) &bull; <code className="text-slate-400">WINDFOR</code> (Day-Ahead Forecasts)
          </div>
          <div className="flex items-center gap-3">
            {dataFreshness && <span>Refreshed: {dataFreshness}</span>}
            <span>All intervals: 30-min Settlement Periods (MW)</span>
          </div>
        </div>
      </footer>
    </div>
  );
};
