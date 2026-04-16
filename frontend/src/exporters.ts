import * as XLSX from 'xlsx';
import html2canvas from 'html2canvas';

export function exportToExcel(analytics: any) {
  const wb = XLSX.utils.book_new();

  const global = analytics?.global || {};
  const deptObj = analytics?.departments || {};

  const rows: any[][] = [
    ['CI Dashboard (Clean)'],
    ['Generated', new Date().toLocaleString()],
    [],
    ['Global KPIs'],
    ['Total LIPT', global.total_lipt ?? 0],
    ['Total Suggestions', global.total_suggestions ?? 0],
    ['Total BP', global.total_bp ?? 0],
    ['Total Kaizen', global.total_kaizen ?? 0],
    ['Total Savings', global.total_savings ?? 0],
    ['Completion Rate (%)', global.completion_rate ?? 0],
    [],
    ['Departments'],
    ['Department', 'Score', 'LIPT (target)', 'LIPT (actual)', 'Suggestions (target)', 'Suggestions (actual)', 'BP (target)', 'BP (actual)', 'Kaizen (target)', 'Kaizen (avg progress)']
  ];

  for (const [name, d] of Object.entries<any>(deptObj)) {
    rows.push([
      name,
      d?.score ?? 0,
      d?.lipt?.target ?? 0,
      d?.lipt?.total ?? 0,
      d?.suggestion?.target ?? 0,
      d?.suggestion?.total ?? 0,
      d?.bp?.target ?? 0,
      d?.bp?.total ?? 0,
      d?.kaizen?.target ?? 0,
      d?.kaizen?.avg_progress ?? 0
    ]);
  }

  const ws = XLSX.utils.aoa_to_sheet(rows);
  XLSX.utils.book_append_sheet(wb, ws, 'Dashboard');

  const filename = `CI_Dashboard_Clean_${new Date().toISOString().slice(0, 10)}.xlsx`;
  XLSX.writeFile(wb, filename);
}

export async function exportToImage(element: HTMLElement) {
  const canvas = await html2canvas(element, { backgroundColor: '#f8fafc', scale: 2 });
  const dataUrl = canvas.toDataURL('image/png');

  const a = document.createElement('a');
  a.href = dataUrl;
  a.download = `CI_Dashboard_Clean_${new Date().toISOString().slice(0, 10)}.png`;
  a.click();
}
