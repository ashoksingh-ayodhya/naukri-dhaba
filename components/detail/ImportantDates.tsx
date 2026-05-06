import type { PostFrontmatter } from "@/lib/types";

export default function ImportantDates({ fm }: { fm: PostFrontmatter }) {
  const dates = fm.dates && Object.keys(fm.dates).length > 0
    ? fm.dates
    : buildFallbackDates(fm);

  if (!Object.keys(dates).length) return null;

  return (
    <div className="card mb-4">
      <div className="px-4 py-3 border-b border-slate-100">
        <h2 className="section-title">📅 Important Dates</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <tbody>
            {Object.entries(dates).map(([label, value], i) => (
              <tr key={label} className={i % 2 === 0 ? "bg-white" : "bg-slate-50"}>
                <td className="px-4 py-2.5 text-sm font-medium text-slate-700 w-1/2 border-r border-slate-100">
                  {label}
                </td>
                <td className="px-4 py-2.5 text-sm text-slate-800 font-semibold">{value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function buildFallbackDates(fm: PostFrontmatter): Record<string, string> {
  const d: Record<string, string> = {};
  if (fm.applicationBegin) d["Application Begin"] = fm.applicationBegin;
  if (fm.lastDate) d["Last Date to Apply"] = fm.lastDate;
  if (fm.examDate) d["Exam Date"] = fm.examDate;
  if (fm.admitDate) d["Admit Card"] = fm.admitDate;
  if (fm.resultDate) d["Result Date"] = fm.resultDate;
  return d;
}
