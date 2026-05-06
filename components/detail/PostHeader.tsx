import { StatusBadge, CategoryBadge } from "@/components/ui/Badge";
import type { PostFrontmatter } from "@/lib/types";

export default function PostHeader({ fm }: { fm: PostFrontmatter }) {
  return (
    <div className="card p-5 mb-4">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <CategoryBadge category={fm.category} dept={fm.dept} />
            <StatusBadge publishedAt={fm.publishedAt} lastDate={fm.lastDate} />
          </div>
          <h1 className="font-heading text-2xl md:text-3xl font-bold text-slate-900 leading-tight mb-2">
            {fm.title}
          </h1>
          <p className="text-slate-500 text-sm">
            <span className="font-medium text-slate-700">{fm.organization}</span>
            {fm.advertisementNo && (
              <span className="ml-2 text-slate-400">· Advt. No: {fm.advertisementNo}</span>
            )}
          </p>
        </div>
      </div>

      {/* Quick stat pills */}
      <div className="mt-4 flex flex-wrap gap-3">
        {fm.totalPosts && (
          <div className="flex items-center gap-1.5 px-3 py-2 bg-blue-50 rounded-lg">
            <span className="text-blue-600 text-lg">👥</span>
            <div>
              <div className="text-xs text-slate-500">Total Posts</div>
              <div className="text-sm font-bold text-slate-800">{fm.totalPosts}</div>
            </div>
          </div>
        )}
        {(fm.ageMin || fm.ageMax) && (
          <div className="flex items-center gap-1.5 px-3 py-2 bg-purple-50 rounded-lg">
            <span className="text-purple-600 text-lg">🎂</span>
            <div>
              <div className="text-xs text-slate-500">Age Limit</div>
              <div className="text-sm font-bold text-slate-800">
                {fm.ageMin}–{fm.ageMax} Years
              </div>
            </div>
          </div>
        )}
        {fm.qualification && (
          <div className="flex items-center gap-1.5 px-3 py-2 bg-green-50 rounded-lg">
            <span className="text-green-600 text-lg">🎓</span>
            <div>
              <div className="text-xs text-slate-500">Qualification</div>
              <div className="text-sm font-bold text-slate-800">{fm.qualification}</div>
            </div>
          </div>
        )}
        {fm.lastDate && (
          <div className="flex items-center gap-1.5 px-3 py-2 bg-red-50 rounded-lg">
            <span className="text-red-600 text-lg">📅</span>
            <div>
              <div className="text-xs text-slate-500">Last Date</div>
              <div className="text-sm font-bold text-slate-800">{fm.lastDate}</div>
            </div>
          </div>
        )}
        {fm.feeGeneral && (
          <div className="flex items-center gap-1.5 px-3 py-2 bg-amber-50 rounded-lg">
            <span className="text-amber-600 text-lg">💰</span>
            <div>
              <div className="text-xs text-slate-500">Fee (General)</div>
              <div className="text-sm font-bold text-slate-800">₹{fm.feeGeneral}/-</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
