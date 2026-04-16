export type UploadKind = 'lipt' | 'suggestion' | 'bp' | 'kaizen';

const DEFAULT_BASE = 'http://localhost:5000/api';

function baseUrl(): string {
  // Allow overriding without changing code.
  return (import.meta as any).env?.VITE_API_BASE_URL || DEFAULT_BASE;
}

async function requestJson<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${baseUrl()}${path}`, {
    ...options,
    headers: {
      ...(options.headers || {})
    }
  });

  const contentType = res.headers.get('content-type') || '';
  let payload: any = null;

  if (contentType.includes('application/json')) {
    payload = await res.json();
  } else {
    const text = await res.text();
    payload = { success: false, error: text };
  }

  if (!res.ok) {
    throw new Error(payload?.error || `HTTP ${res.status}`);
  }
  if (payload?.success === false) {
    throw new Error(payload?.error || 'Request failed');
  }

  return payload as T;
}

export const api = {
  health: () => requestJson<{ success: true; status: string }>(`/health`),

  session: () => requestJson<{ success: true; data: { uploaded: Record<UploadKind, boolean> } }>(`/session`),

  upload: async (kind: UploadKind, file: File) => {
    const form = new FormData();
    form.append('file', file);
    return requestJson<{ success: true; data: any }>(`/upload/${kind}`, {
      method: 'POST',
      body: form
    });
  },

  calculate: () => requestJson<{ success: true; data: any }>(`/analytics/calculate`, { method: 'POST' }),

  reset: () => requestJson<{ success: true }>(`/reset`, { method: 'POST' })
};
