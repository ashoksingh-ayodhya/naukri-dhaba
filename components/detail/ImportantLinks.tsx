import type { PostFrontmatter, ImportantLink } from "@/lib/types";

const LINK_TYPE_CONFIG: Record<string, { label: string; color: string }> = {
  apply: { label: "Apply Online", color: "bg-green-600 hover:bg-green-700 text-white" },
  notification: { label: "Official Notification", color: "bg-blue-600 hover:bg-blue-700 text-white" },
  result: { label: "Result", color: "bg-purple-600 hover:bg-purple-700 text-white" },
  admit: { label: "Admit Card", color: "bg-orange-500 hover:bg-orange-600 text-white" },
  answer_key: { label: "Answer Key", color: "bg-teal-600 hover:bg-teal-700 text-white" },
  syllabus: { label: "Syllabus", color: "bg-indigo-600 hover:bg-indigo-700 text-white" },
  exam_city: { label: "Exam City", color: "bg-cyan-600 hover:bg-cyan-700 text-white" },
  eligibility: { label: "Eligibility", color: "bg-amber-500 hover:bg-amber-600 text-white" },
  official_website: { label: "Official Website", color: "bg-slate-600 hover:bg-slate-700 text-white" },
  other: { label: "Link", color: "bg-slate-500 hover:bg-slate-600 text-white" },
};

export default function ImportantLinks({ fm }: { fm: PostFrontmatter }) {
  const links: ImportantLink[] = [];

  if (fm.importantLinks?.length) {
    links.push(...fm.importantLinks);
  } else {
    if (fm.applyUrl && fm.applyUrl !== "#") links.push({ label: "Apply Online", url: fm.applyUrl, link_type: "apply" });
    if (fm.notificationUrl) links.push({ label: "Official Notification PDF", url: fm.notificationUrl, link_type: "notification" });
    if (fm.resultUrl && fm.resultUrl !== "#") links.push({ label: "Result", url: fm.resultUrl, link_type: "result" });
    if (fm.admitUrl && fm.admitUrl !== "#") links.push({ label: "Admit Card", url: fm.admitUrl, link_type: "admit" });
    if (fm.officialWebsite) links.push({ label: "Official Website", url: fm.officialWebsite, link_type: "official_website" });
  }

  if (!links.length) return null;

  return (
    <div className="card mb-4">
      <div className="px-4 py-3 border-b border-slate-100">
        <h2 className="section-title">🔗 Important Links</h2>
      </div>
      <div className="p-4">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <tbody>
              {links.map((link, i) => {
                const cfg = LINK_TYPE_CONFIG[link.link_type] || LINK_TYPE_CONFIG.other;
                const isActive = link.url && link.url !== "#";
                return (
                  <tr key={i} className={i % 2 === 0 ? "bg-white" : "bg-slate-50"}>
                    <td className="px-3 py-2.5 font-medium text-slate-700">{link.label}</td>
                    <td className="px-3 py-2.5 text-right">
                      {isActive ? (
                        <a
                          href={`/go/?url=${encodeURIComponent(link.url)}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className={`inline-flex items-center px-4 py-1.5 rounded-lg text-xs font-semibold transition-colors ${cfg.color}`}
                        >
                          {cfg.label} ↗
                        </a>
                      ) : (
                        <span className="inline-flex items-center px-4 py-1.5 rounded-lg text-xs font-semibold bg-slate-100 text-slate-400">
                          Not Available
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
