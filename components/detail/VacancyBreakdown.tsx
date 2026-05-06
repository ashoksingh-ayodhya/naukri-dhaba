import type { PostFrontmatter } from "@/lib/types";

export default function VacancyBreakdown({ fm }: { fm: PostFrontmatter }) {
  if (!fm.vacancyBreakdown?.length) return null;

  const rows = fm.vacancyBreakdown;
  const hasGeneral = rows.some((r) => r.general);
  const hasEWS = rows.some((r) => r.ews);
  const hasOBC = rows.some((r) => r.obc);
  const hasSC = rows.some((r) => r.sc);
  const hasST = rows.some((r) => r.st);
  const hasEligibility = rows.some((r) => r.eligibility);

  return (
    <div className="card mb-4">
      <div className="px-4 py-3 border-b border-slate-100">
        <h2 className="section-title">
          👥 Vacancy Details
          {fm.totalPosts && (
            <span className="ml-2 text-base font-normal text-slate-500">
              Total: <span className="font-bold text-primary-900">{fm.totalPosts}</span>
            </span>
          )}
        </h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="table-header text-xs">
              <th className="px-3 py-2 text-left">Post Name</th>
              {hasGeneral && <th className="px-3 py-2 text-center">UR</th>}
              {hasEWS && <th className="px-3 py-2 text-center">EWS</th>}
              {hasOBC && <th className="px-3 py-2 text-center">OBC</th>}
              {hasSC && <th className="px-3 py-2 text-center">SC</th>}
              {hasST && <th className="px-3 py-2 text-center">ST</th>}
              <th className="px-3 py-2 text-center">Total</th>
              {hasEligibility && <th className="px-3 py-2 text-left">Eligibility</th>}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className={i % 2 === 0 ? "bg-white" : "bg-slate-50"}>
                <td className="px-3 py-2 font-medium text-slate-800">{row.post_name}</td>
                {hasGeneral && <td className="px-3 py-2 text-center text-slate-600">{row.general || "—"}</td>}
                {hasEWS && <td className="px-3 py-2 text-center text-slate-600">{row.ews || "—"}</td>}
                {hasOBC && <td className="px-3 py-2 text-center text-slate-600">{row.obc || "—"}</td>}
                {hasSC && <td className="px-3 py-2 text-center text-slate-600">{row.sc || "—"}</td>}
                {hasST && <td className="px-3 py-2 text-center text-slate-600">{row.st || "—"}</td>}
                <td className="px-3 py-2 text-center font-bold text-primary-900">{row.total || "—"}</td>
                {hasEligibility && <td className="px-3 py-2 text-slate-600 text-xs">{row.eligibility || "—"}</td>}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
