// Thin fetch helpers over the backend (proxied at /api -> :8600).

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`/api${path}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error((await r.text()) || `${r.status} ${r.statusText}`);
  return r.json() as Promise<T>;
}

export interface CrawlResult {
  hub_url: string;
  found: number;
  ingested: number;
  failed: number;
  notes: string[];
  results: { url: string; status: 'ok' | 'error'; title?: string; notes?: string[]; error?: string }[];
}

export interface IngestResult {
  url: string;
  title: string;
  mode: string;
  notes: string[];
}
