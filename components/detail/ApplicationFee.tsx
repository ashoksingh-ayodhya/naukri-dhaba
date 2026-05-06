import type { PostFrontmatter } from "@/lib/types";

export default function ApplicationFee({ fm }: { fm: PostFrontmatter }) {
  const fees = fm.fees && Object.keys(fm.fees).length > 0
    ? fm.fees
    : buildFallbackFees(fm);

  if (!Object.keys(fees).length) return null;

  return (
    <div className="card mb-4">
      <div className="px-4 py-3 border-b border-slate-100">
        <h2 className="section-title">💰 Application Fee</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <tbody>
            {Object.entries(fees).map(([label, value], i) => (
              <tr key={label} className={i % 2 === 0 ? "bg-white" : "bg-slate-50"}>
                <td className="px-4 py-2.5 text-sm font-medium text-slate-700 w-1/2 border-r border-slate-100">
                  {label}
                </td>
                <td className="px-4 py-2.5 text-sm text-slate-800 font-semibold">₹{value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {fm.feePaymentMethod && (
        <div className="px-4 py-2 bg-slate-50 border-t border-slate-100 text-xs text-slate-500">
          Payment Mode: <span className="font-medium text-slate-700">{fm.feePaymentMethod}</span>
        </div>
      )}
    </div>
  );
}

function buildFallbackFees(fm: PostFrontmatter): Record<string, string> {
  const f: Record<string, string> = {};
  if (fm.feeGeneral) f["General / OBC / EWS"] = fm.feeGeneral;
  if (fm.feeSCST) f["SC / ST"] = fm.feeSCST;
  return f;
}
