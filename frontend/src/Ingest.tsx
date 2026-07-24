import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiPost, type CrawlResult, type IngestResult } from './api';

type Mode = 'single' | 'crawl';

const box: React.CSSProperties = { border: '1px solid #e2e2e2', borderRadius: 8, padding: 16 };
const input: React.CSSProperties = { padding: '8px 10px', borderRadius: 6, border: '1px solid #ccc', width: '100%', boxSizing: 'border-box' };
const btn: React.CSSProperties = { padding: '8px 16px', borderRadius: 6, border: '1px solid #0f6b5c', background: '#0f6b5c', color: '#fff', cursor: 'pointer' };

export default function Ingest() {
  const qc = useQueryClient();
  const [source, setSource] = useState<Mode>('crawl');
  const [url, setUrl] = useState('https://learn.microsoft.com/en-us/azure/architecture/ai-ml/ai-get-started');
  const [mode, setMode] = useState<'article' | 'paper'>('article');
  const [atomic, setAtomic] = useState(true);
  const [limit, setLimit] = useState(50);
  const [sameDomain, setSameDomain] = useState(true);
  const [pathContains, setPathContains] = useState('');

  const refreshHealth = () => qc.invalidateQueries({ queryKey: ['health'] });

  const single = useMutation({
    mutationFn: () => apiPost<IngestResult>('/ingest/url', { url, mode, atomic }),
    onSuccess: refreshHealth,
  });
  const crawl = useMutation({
    mutationFn: () =>
      apiPost<CrawlResult>('/ingest/crawl', {
        url, mode, atomic, limit,
        same_domain: sameDomain,
        path_contains: pathContains || null,
      }),
    onSuccess: refreshHealth,
  });

  const busy = single.isPending || crawl.isPending;
  const run = () => (source === 'single' ? single.mutate() : crawl.mutate());

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div style={{ display: 'flex', gap: 8 }}>
        {(['crawl', 'single'] as Mode[]).map(m => (
          <button key={m} onClick={() => setSource(m)}
            style={{ ...btn, background: source === m ? '#0f6b5c' : '#fff', color: source === m ? '#fff' : '#222', borderColor: '#ccc' }}>
            {m === 'crawl' ? 'Crawl a hub page' : 'Single URL'}
          </button>
        ))}
      </div>

      <div style={box}>
        <label style={{ fontSize: 13, color: '#555' }}>{source === 'crawl' ? 'Hub / index page URL' : 'Page URL'}</label>
        <input style={{ ...input, marginTop: 6 }} value={url} onChange={e => setUrl(e.target.value)}
          placeholder="https://..." />

        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginTop: 12, alignItems: 'center', fontSize: 14 }}>
          <label>Mode{' '}
            <select value={mode} onChange={e => setMode(e.target.value as 'article' | 'paper')}>
              <option value="article">article</option>
              <option value="paper">paper</option>
            </select>
          </label>
          <label><input type="checkbox" checked={atomic} onChange={e => setAtomic(e.target.checked)} /> atomic notes</label>
          {source === 'crawl' && (
            <>
              <label>limit{' '}
                <input type="number" min={1} value={limit} onChange={e => setLimit(Number(e.target.value))}
                  style={{ width: 64 }} />
              </label>
              <label><input type="checkbox" checked={sameDomain} onChange={e => setSameDomain(e.target.checked)} /> same domain only</label>
              <label>path contains{' '}
                <input value={pathContains} onChange={e => setPathContains(e.target.value)}
                  placeholder="/architecture/" style={{ width: 140 }} />
              </label>
            </>
          )}
        </div>

        <div style={{ marginTop: 14 }}>
          <button style={{ ...btn, opacity: busy ? 0.6 : 1 }} disabled={busy} onClick={run}>
            {busy ? 'Working...' : source === 'crawl' ? 'Crawl + ingest all resources' : 'Ingest'}
          </button>
        </div>
      </div>

      {single.error && <Err e={single.error} />}
      {crawl.error && <Err e={crawl.error} />}
      {single.data && <SingleResult r={single.data} />}
      {crawl.data && <CrawlResultView r={crawl.data} />}
    </div>
  );
}

function Err({ e }: { e: unknown }) {
  return <div style={{ ...box, borderColor: '#c0392b', color: '#c0392b' }}>Error: {String((e as Error).message)}</div>;
}

function SingleResult({ r }: { r: IngestResult }) {
  return (
    <div style={box}>
      <strong>{r.title}</strong> <span style={{ color: '#888' }}>({r.mode})</span>
      <p style={{ color: '#555', margin: '6px 0 0' }}>Wrote {r.notes.length} note(s).</p>
      <NoteList notes={r.notes} />
    </div>
  );
}

function CrawlResultView({ r }: { r: CrawlResult }) {
  return (
    <div style={box}>
      <div style={{ display: 'flex', gap: 16, fontSize: 15 }}>
        <span><strong>{r.found}</strong> found</span>
        <span style={{ color: '#0f6b5c' }}><strong>{r.ingested}</strong> ingested</span>
        {r.failed > 0 && <span style={{ color: '#c0392b' }}><strong>{r.failed}</strong> failed</span>}
        <span style={{ color: '#888' }}>{r.notes.length} notes written</span>
      </div>
      <ul style={{ marginTop: 12, paddingLeft: 18, maxHeight: 320, overflow: 'auto' }}>
        {r.results.map(res => (
          <li key={res.url} style={{ marginBottom: 6, fontSize: 13 }}>
            <span style={{ color: res.status === 'ok' ? '#0f6b5c' : '#c0392b' }}>
              {res.status === 'ok' ? '✓' : '✗'}
            </span>{' '}
            {res.title || res.url}
            {res.status === 'error' && <span style={{ color: '#c0392b' }}> - {res.error}</span>}
            {res.notes && res.notes.length > 1 && <span style={{ color: '#888' }}> ({res.notes.length} notes)</span>}
          </li>
        ))}
      </ul>
    </div>
  );
}

function NoteList({ notes }: { notes: string[] }) {
  return (
    <ul style={{ marginTop: 6, paddingLeft: 18, fontSize: 12, color: '#666' }}>
      {notes.map(n => <li key={n}>{n.split('/').slice(-2).join('/')}</li>)}
    </ul>
  );
}
