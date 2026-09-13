/** "500" → "₹500"; "No Fee" / "Rs. 500/-" are shown as written. */
export function formatFee(value: string | undefined): string {
  if (!value) return "";
  const v = value.trim();
  return /^\d+$/.test(v) ? `₹${Number(v).toLocaleString("en-IN")}` : v;
}
