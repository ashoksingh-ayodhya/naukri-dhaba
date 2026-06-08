/**
 * Date-badge helpers — pure functions with no Node.js dependencies.
 * Kept separate from lib/content.ts (which imports `fs`) so client
 * components (e.g. MobileJobCard, StatusBadge) can use them without
 * pulling Node-only modules into the browser bundle.
 */

export function parseDDMMYYYY(dateStr: string | undefined): Date | null {
  if (!dateStr) return null;
  // Accept both DD/MM/YYYY and DD-MM-YYYY (scraper writes either)
  const match = dateStr.match(/(\d{2})[\/\-](\d{2})[\/\-](\d{4})/);
  if (!match) return null;
  const [, dd, mm, yyyy] = match;
  const d = new Date(`${yyyy}-${mm}-${dd}`);
  return isNaN(d.getTime()) ? null : d;
}

export function isNew(publishedAt: string): boolean {
  const today = new Date();
  const pub = new Date(publishedAt);
  const diffMs = today.getTime() - pub.getTime();
  const diffDays = diffMs / (1000 * 60 * 60 * 24);
  return diffDays <= 3;
}

export function isDeadlineSoon(lastDate: string | undefined): boolean {
  const deadline = parseDDMMYYYY(lastDate);
  if (!deadline) return false;
  const diffDays = (deadline.getTime() - Date.now()) / (1000 * 60 * 60 * 24);
  return diffDays >= 0 && diffDays <= 7;
}

export function isExpired(lastDate: string | undefined): boolean {
  const deadline = parseDDMMYYYY(lastDate);
  if (!deadline) return false;
  return deadline < new Date();
}
