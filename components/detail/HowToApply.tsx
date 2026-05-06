import type { PostFrontmatter } from "@/lib/types";

export default function HowToApply({ fm }: { fm: PostFrontmatter }) {
  if (!fm.howToApply?.length) return null;

  return (
    <div className="card mb-4">
      <div className="px-4 py-3 border-b border-slate-100">
        <h2 className="section-title">📝 How to Apply</h2>
      </div>
      <ol className="px-4 py-4 space-y-3 list-none">
        {fm.howToApply.map((step, i) => (
          <li key={i} className="flex gap-3">
            <span className="shrink-0 w-6 h-6 rounded-full bg-primary-900 text-white text-xs font-bold flex items-center justify-center mt-0.5">
              {i + 1}
            </span>
            <p className="text-sm text-slate-700 leading-relaxed">{step}</p>
          </li>
        ))}
      </ol>
    </div>
  );
}
