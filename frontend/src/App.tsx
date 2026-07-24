import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import Ingest from './Ingest';

// Tabs map 1:1 to backend routes. Panels get built out per STATUS.md.
const TABS = ['Ask', 'Search', 'Graph', 'Ingest', 'Blog', 'Settings'] as const;
type Tab = (typeof TABS)[number];

export default function App() {
  const [tab, setTab] = useState<Tab>('Ask');
  const health = useQuery({
    queryKey: ['health'],
    queryFn: () => fetch('/api/health').then(r => r.json()),
  });

  return (
    <div style={{ fontFamily: 'system-ui', maxWidth: 900, margin: '0 auto', padding: 24 }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <h1 style={{ fontSize: 20 }}>Knowledge Pipeline</h1>
        <span style={{ fontSize: 13, color: '#666' }}>
          {health.data ? `${health.data.chunks_indexed} chunks indexed` : 'backend offline'}
        </span>
      </header>
      <nav style={{ display: 'flex', gap: 8, margin: '16px 0' }}>
        {TABS.map(t => (
          <button key={t} onClick={() => setTab(t)}
                  style={{ padding: '6px 14px', borderRadius: 6, border: '1px solid #ccc',
                           background: tab === t ? '#0f6b5c' : '#fff',
                           color: tab === t ? '#fff' : '#222', cursor: 'pointer' }}>
            {t}
          </button>
        ))}
      </nav>
      <main style={{ border: '1px solid #e2e2e2', borderRadius: 8, padding: 24, minHeight: 320 }}>
        {tab === 'Ingest' ? (
          <Ingest />
        ) : (
          <p style={{ color: '#666' }}>
            {tab} panel - not yet implemented. Backend routes are live; see STATUS.md for the build
            order (Ask with citations first, then Search score breakdown, Graph view, Ingest
            dashboard, Blog manager, Settings).
          </p>
        )}
      </main>
    </div>
  );
}
