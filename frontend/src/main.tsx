import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Layout, type TabType } from './components/Layout';
import { OverviewPage } from './pages/OverviewPage';
import { SeriesPage } from './pages/SeriesPage';
import { AccuracyPage } from './pages/AccuracyPage';
import { VintagesPage } from './pages/VintagesPage';
import { ProvenancePage } from './pages/ProvenancePage';
import './index.css';

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('overview');

  const renderPage = () => {
    if (activeTab === 'overview') return <OverviewPage />;
    if (activeTab === 'series') return <SeriesPage />;
    if (activeTab === 'accuracy') return <AccuracyPage />;
    if (activeTab === 'vintages') return <VintagesPage />;
    if (activeTab === 'quality') return <ProvenancePage />;

    return <OverviewPage />;
  };

  return (
    <Layout activeTab={activeTab} onTabChange={setActiveTab}>
      {renderPage()}
    </Layout>
  );
};

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
