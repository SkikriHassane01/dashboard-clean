import './styles.css';

import { api, type UploadKind } from './api';
import { detectKind } from './upload_detect';
import { exportToExcel, exportToImage } from './exporters';

type UploadState = Record<UploadKind, { uploaded: boolean; name?: string; note?: string }>;

const state: {
  uploads: UploadState;
  analytics: any | null;
} = {
  uploads: {
    lipt: { uploaded: false },
    suggestion: { uploaded: false },
    bp: { uploaded: false },
    kaizen: { uploaded: false }
  },
  analytics: null
};

function el<K extends keyof HTMLElementTagNameMap>(tag: K, className?: string): HTMLElementTagNameMap[K] {
  const e = document.createElement(tag);
  if (className) e.className = className;
  return e;
}

function escapeHtml(value: unknown): string {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function toast(msg: string, type: 'ok' | 'err' | 'info' = 'info') {
  const root = document.getElementById('toast-root')!;
  const t = el('div', `pointer-events-auto toast toast-${type}`);
  t.textContent = msg;
  t.setAttribute('role', 'status');
  root.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

function render() {
  const app = document.getElementById('app')!;
  app.innerHTML = '';

  const shell = el('div', 'min-h-screen');

  const header = el('header', 'sticky top-0 z-40 border-b border-white/40 bg-white/70 backdrop-blur');
  header.innerHTML = `
    <div class="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between gap-4">
      <div class="flex items-center gap-3">
        <div class="h-10 w-10 rounded-xl bg-gradient-to-br from-indigo-600 to-sky-500 text-white shadow-sm flex items-center justify-center">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            <path d="M4 19V5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <path d="M8 19V12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <path d="M12 19V9" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <path d="M16 19V14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <path d="M20 19V7" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </div>
        <div>
          <div class="text-xl font-semibold leading-tight">
            <span class="bg-gradient-to-r from-slate-900 to-slate-600 bg-clip-text text-transparent">CI Dashboard</span>
            <span class="ml-2 chip chip-info align-middle">Clean</span>
          </div>
          <div class="text-sm text-slate-600">Upload Excel files (or a folder), analyze, and export results.</div>
        </div>
      </div>
      <div class="flex items-center gap-2 no-print">
        <button id="btnReset" class="btn btn-secondary">Reset</button>
        <button id="btnHealth" class="btn btn-secondary">Health</button>
      </div>
    </div>
  `;

  const main = el('main', 'max-w-6xl mx-auto px-4 py-8 space-y-6');

  // Upload section
  const uploadCard = el('section', 'card card-hover p-5');
  uploadCard.innerHTML = `
    <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
      <div class="space-y-1">
        <div class="flex items-center gap-2">
          <span class="chip chip-miss">Step 1</span>
          <div class="font-semibold">Upload</div>
        </div>
        <div class="text-sm text-slate-600">Upload a folder (auto-detect) or upload each Excel file type manually.</div>
      </div>
      <div class="flex flex-wrap items-center gap-2 no-print">
        <input id="folderInput" type="file" webkitdirectory directory multiple class="hidden" />
        <button id="btnFolder" class="btn btn-primary">Upload folder</button>

        <span class="h-6 w-px bg-slate-200 mx-1 hidden md:block" aria-hidden="true"></span>

        <input id="fileLipt" type="file" accept=".xlsx,.xls" class="hidden" />
        <input id="fileSugg" type="file" accept=".xlsx,.xls" class="hidden" />
        <input id="fileBp" type="file" accept=".xlsx,.xls" class="hidden" />
        <input id="fileKaizen" type="file" accept=".xlsx,.xls" class="hidden" />

        <button data-kind="lipt" class="btnKind btn btn-secondary">LIPT</button>
        <button data-kind="suggestion" class="btnKind btn btn-secondary">Suggestions</button>
        <button data-kind="bp" class="btnKind btn btn-secondary">BP</button>
        <button data-kind="kaizen" class="btnKind btn btn-secondary">Kaizen</button>
      </div>
    </div>

    <div class="mt-5 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
      ${(['lipt', 'suggestion', 'bp', 'kaizen'] as UploadKind[])
        .map((k) => {
          const s = state.uploads[k];
          const label = k === 'bp' ? 'BP' : k === 'lipt' ? 'LIPT' : k === 'kaizen' ? 'KAIZEN' : 'SUGGESTIONS';
          return `
          <div class="stat ${s.uploaded ? 'stat-ok' : 'stat-miss'}">
            <div class="flex items-start justify-between gap-2">
              <div class="min-w-0">
                <div class="flex items-center gap-2">
                  <span class="h-2.5 w-2.5 rounded-full ${s.uploaded ? 'bg-emerald-500' : 'bg-slate-300'}" aria-hidden="true"></span>
                  <div class="font-semibold tracking-wide">${label}</div>
                </div>
                <div class="mt-2 text-xs text-slate-600 break-words">${s.name ? escapeHtml(s.name) : '—'}</div>
              </div>
              <span class="chip ${s.uploaded ? 'chip-ok' : 'chip-miss'}">${s.uploaded ? 'Uploaded' : 'Missing'}</span>
            </div>
            ${s.note ? `<div class="mt-3 text-xs text-slate-600">${escapeHtml(s.note)}</div>` : ''}
          </div>
        `;
        })
        .join('')}
    </div>

    <div class="mt-5 flex flex-col md:flex-row md:items-center md:justify-between gap-3">
      <div class="text-sm text-slate-600">Analyze becomes available after any successful upload.</div>
      <button id="btnAnalyze" class="btn ${canAnalyze() ? 'btn-neutral' : 'btn-disabled'}" ${canAnalyze() ? '' : 'disabled'}>Analyze</button>
    </div>
  `;

  // Results
  const results = el('section', 'card p-5');
  results.id = 'results';
  results.innerHTML = state.analytics
    ? renderResultsHtml(state.analytics)
    : `
      <div class="flex items-center justify-between gap-4">
        <div class="space-y-1">
          <div class="flex items-center gap-2">
            <span class="chip chip-miss">Step 2</span>
            <div class="font-semibold">Results</div>
          </div>
          <div class="text-sm text-slate-600">Run analysis to see KPIs and the department breakdown.</div>
        </div>
      </div>
    `;

  main.appendChild(uploadCard);
  main.appendChild(results);

  const toastRoot = el('div', 'fixed top-4 right-4 z-50 space-y-2 pointer-events-none');
  toastRoot.id = 'toast-root';

  shell.appendChild(header);
  shell.appendChild(main);
  shell.appendChild(toastRoot);
  app.appendChild(shell);

  wireEvents();
}

function renderResultsHtml(analytics: any): string {
  const g = analytics?.global || {};
  const depts = analytics?.departments || {};

  const rows = Object.entries<any>(depts).map(([name, d]) => {
    const l = d?.lipt || {};
    const s = d?.suggestion || {};
    const b = d?.bp || {};
    const k = d?.kaizen || {};

    return `
      <tr class="hover:bg-slate-50/70 transition-colors">
        <td class="py-3 px-3 font-medium">${escapeHtml(name)}</td>
        <td class="py-3 px-3 text-right tabular-nums">${d?.score ?? 0}%</td>
        <td class="py-3 px-3 text-right tabular-nums">${l.total ?? 0} / ${l.target ?? 0}</td>
        <td class="py-3 px-3 text-right tabular-nums">${s.total ?? 0} / ${s.target ?? 0}</td>
        <td class="py-3 px-3 text-right tabular-nums">${b.total ?? 0} / ${b.target ?? 0}</td>
        <td class="py-3 px-3 text-right tabular-nums">${k.avg_progress ?? 0}%</td>
        <td class="py-3 px-3 text-right tabular-nums">$${Number(l.savings ?? 0).toLocaleString()}</td>
      </tr>
    `;
  });

  return `
    <div class="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
      <div class="space-y-1">
        <div class="flex items-center gap-2">
          <span class="chip chip-miss">Step 2</span>
          <div class="font-semibold">Results</div>
        </div>
        <div class="text-sm text-slate-600">Global KPIs and department table.</div>
      </div>
      <div class="flex flex-wrap gap-2 no-print">
        <button id="btnExcel" class="btn btn-secondary">Export Excel</button>
        <button id="btnPDF" class="btn btn-secondary">Export PDF</button>
        <button id="btnImage" class="btn btn-secondary">Export Image</button>
      </div>
    </div>

    <div id="captureArea" class="mt-5 space-y-4">
      <div class="grid grid-cols-2 md:grid-cols-6 gap-3">
        ${kpiCard('Total LIPT', g.total_lipt ?? 0)}
        ${kpiCard('Suggestions', g.total_suggestions ?? 0)}
        ${kpiCard('Best Practices', g.total_bp ?? 0)}
        ${kpiCard('Kaizen events', g.total_kaizen ?? 0)}
        ${kpiCard('Savings', `$${Number(g.total_savings ?? 0).toLocaleString()}`)}
        ${kpiCard('Completion', `${g.completion_rate ?? 0}%`)}
      </div>

      <div class="overflow-x-auto rounded-xl border border-slate-200 bg-white/60">
        <table class="min-w-full text-sm">
          <thead class="sticky top-0 bg-slate-50/90 text-slate-700 backdrop-blur">
            <tr>
              <th class="text-left py-2.5 px-3 font-semibold">Department</th>
              <th class="text-right py-2.5 px-3 font-semibold">Score</th>
              <th class="text-right py-2.5 px-3 font-semibold">LIPT</th>
              <th class="text-right py-2.5 px-3 font-semibold">Suggestions</th>
              <th class="text-right py-2.5 px-3 font-semibold">BP</th>
              <th class="text-right py-2.5 px-3 font-semibold">Kaizen</th>
              <th class="text-right py-2.5 px-3 font-semibold">Savings</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-100 bg-white/70">
            ${rows.join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function kpiCard(label: string, value: string | number): string {
  return `
    <div class="card p-4">
      <div class="text-xs text-slate-500">${escapeHtml(label)}</div>
      <div class="mt-1 text-2xl font-semibold tracking-tight tabular-nums">${escapeHtml(value)}</div>
    </div>
  `;
}

function canAnalyze(): boolean {
  return Object.values(state.uploads).some((u) => u.uploaded);
}

function wireEvents() {
  const btnFolder = document.getElementById('btnFolder') as HTMLButtonElement;
  const folderInput = document.getElementById('folderInput') as HTMLInputElement;

  btnFolder.addEventListener('click', () => folderInput.click());
  folderInput.addEventListener('change', async () => {
    const files = Array.from(folderInput.files || []);
    folderInput.value = '';
    await handleFolderFiles(files);
  });

  // per-kind uploads
  const fileLipt = document.getElementById('fileLipt') as HTMLInputElement;
  const fileSugg = document.getElementById('fileSugg') as HTMLInputElement;
  const fileBp = document.getElementById('fileBp') as HTMLInputElement;
  const fileKaizen = document.getElementById('fileKaizen') as HTMLInputElement;

  const inputByKind: Record<UploadKind, HTMLInputElement> = {
    lipt: fileLipt,
    suggestion: fileSugg,
    bp: fileBp,
    kaizen: fileKaizen
  };

  document.querySelectorAll<HTMLButtonElement>('.btnKind').forEach((b) => {
    b.addEventListener('click', () => {
      const kind = b.dataset.kind as UploadKind;
      inputByKind[kind].click();
    });
  });

  for (const [kind, input] of Object.entries(inputByKind) as [UploadKind, HTMLInputElement][]) {
    input.addEventListener('change', async () => {
      const file = input.files?.[0];
      input.value = '';
      if (!file) return;
      await uploadOne(kind, file);
    });
  }

  const btnAnalyze = document.getElementById('btnAnalyze') as HTMLButtonElement;
  btnAnalyze?.addEventListener('click', async () => {
    if (!canAnalyze()) return;
    await analyze();
  });

  const btnReset = document.getElementById('btnReset') as HTMLButtonElement;
  btnReset.addEventListener('click', async () => {
    await api.reset();
    state.analytics = null;
    for (const k of Object.keys(state.uploads) as UploadKind[]) {
      state.uploads[k] = { uploaded: false };
    }
    toast('Session reset', 'ok');
    render();
  });

  const btnHealth = document.getElementById('btnHealth') as HTMLButtonElement;
  btnHealth.addEventListener('click', async () => {
    try {
      await api.health();
      toast('Backend is healthy', 'ok');
    } catch (e: any) {
      toast(`Backend unreachable: ${e?.message || e}`, 'err');
    }
  });

  const btnExcel = document.getElementById('btnExcel') as HTMLButtonElement | null;
  btnExcel?.addEventListener('click', () => {
    if (!state.analytics) return;
    exportToExcel(state.analytics);
  });

  const btnPDF = document.getElementById('btnPDF') as HTMLButtonElement | null;
  btnPDF?.addEventListener('click', () => window.print());

  const btnImage = document.getElementById('btnImage') as HTMLButtonElement | null;
  btnImage?.addEventListener('click', async () => {
    const area = document.getElementById('captureArea') as HTMLElement | null;
    if (!area) return;
    await exportToImage(area);
  });
}

async function uploadOne(kind: UploadKind, file: File) {
  try {
    toast(`Uploading ${kind.toUpperCase()}...`, 'info');
    const res = await api.upload(kind, file);
    const info = (res as any).data || {};
    state.uploads[kind] = {
      uploaded: true,
      name: file.name,
      note: `valid: ${info.valid_rows ?? 0}, skipped: ${info.skipped_rows ?? 0}`
    };
    toast(`${kind.toUpperCase()} uploaded`, 'ok');
    render();
  } catch (e: any) {
    toast(`${kind.toUpperCase()} upload failed: ${e?.message || e}`, 'err');
  }
}

async function handleFolderFiles(files: File[]) {
  if (files.length === 0) return;

  // auto-detect: pick at most one file per kind (first match wins)
  const picked: Partial<Record<UploadKind, File>> = {};
  const unknown: string[] = [];

  const kinds: UploadKind[] = ['lipt', 'suggestion', 'bp', 'kaizen'];

  for (const f of files) {
    if (kinds.every((k) => Boolean(picked[k]))) break;
    if (!f.name) continue;

    const kind = await detectKind(f);
    if (!kind) {
      unknown.push(f.name);
      continue;
    }

    if (!picked[kind]) picked[kind] = f;
  }

  for (const [k, f] of Object.entries(picked) as [UploadKind, File][]) {
    await uploadOne(k, f);
  }

  if (unknown.length > 0) {
    toast(`Skipped ${unknown.length} unknown file(s) from folder`, 'info');
  }

  if (!canAnalyze()) {
    toast('No supported Excel files detected in folder', 'err');
  }
}

async function analyze() {
  try {
    toast('Analyzing...', 'info');
    const res = await api.calculate();
    state.analytics = (res as any).data;
    toast('Analysis complete', 'ok');
    render();
  } catch (e: any) {
    toast(`Analyze failed: ${e?.message || e}`, 'err');
  }
}

async function boot() {
  render();

  try {
    await api.health();
  } catch {
    toast('Start backend on http://localhost:5000', 'info');
  }
}

boot();
