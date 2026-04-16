import * as XLSX from 'xlsx';
import type { UploadKind } from './api';

const extOk = (name: string) => {
  const ext = name.split('.').pop()?.toLowerCase();
  return ext === 'xlsx' || ext === 'xls';
};

const byName = (name: string): UploadKind | null => {
  const n = name.toLowerCase();
  if (n.includes('lipt') || n.includes('improvement')) return 'lipt';
  if (n.includes('sugg') || n.includes('suggest') || n.includes('cisbox')) return 'suggestion';
  if (/(^|\W)bp(\W|$)/.test(n) || n.includes('best practice') || n.includes('best_practice')) return 'bp';
  if (n.includes('kaizen')) return 'kaizen';
  return null;
};

const headerHas = (headers: string[], needle: string) =>
  headers.some((h) => h.includes(needle));

const normalizeHeader = (v: unknown) => String(v ?? '').trim().toLowerCase();

export async function detectKind(file: File): Promise<UploadKind | null> {
  if (!extOk(file.name)) return null;

  const guess = byName(file.name);
  if (guess) return guess;

  // Fallback: inspect first row headers.
  const buf = await file.arrayBuffer();
  const wb = XLSX.read(buf, { type: 'array' });
  const firstSheetName = wb.SheetNames[0];
  const sheet = wb.Sheets[firstSheetName];

  const rows = XLSX.utils.sheet_to_json(sheet, { header: 1, range: 0, blankrows: false }) as unknown[][];
  const headerRow = (rows[0] || []).map(normalizeHeader).filter(Boolean);

  if (headerRow.length === 0) return null;

  // LIPT
  if (headerHas(headerRow, 'annual savings') || headerHas(headerRow, 'savings') || headerHas(headerRow, 'improvement category')) return 'lipt';

  // Suggestions
  if (headerHas(headerRow, 'suggestion') || headerHas(headerRow, "type d'amélioration") || headerHas(headerRow, 'improvement type')) return 'suggestion';

  // BP
  if (headerHas(headerRow, 'bp title') || headerHas(headerRow, 'best practice')) return 'bp';

  // Kaizen
  if (headerHas(headerRow, 'progress') || headerHas(headerRow, 'avancement') || headerHas(headerRow, 'progrès')) return 'kaizen';

  return null;
}
