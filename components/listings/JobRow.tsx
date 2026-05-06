import Link from "next/link";
import { StatusBadge, CategoryBadge } from "@/components/ui/Badge";
import type { ListingPost } from "@/lib/types";

interface JobRowProps {
  post: ListingPost;
  index: number;
}

export default function JobRow({ post, index }: JobRowProps) {
  return (
    <tr className={index % 2 === 0 ? "table-row-even" : "table-row-odd"}>
      <td className="px-4 py-3">
        <div className="flex items-start gap-2">
          <div>
            <Link
              href={post.href}
              className="text-sm font-medium text-primary-900 hover:text-primary-700 hover:underline transition-colors leading-snug"
            >
              {post.title}
            </Link>
            <div className="flex items-center gap-2 mt-1">
              <CategoryBadge category={post.category} dept={post.dept} />
              <span className="text-xs text-slate-400">{post.organization}</span>
            </div>
          </div>
        </div>
      </td>
      <td className="px-4 py-3 text-center hidden sm:table-cell">
        <span className="text-sm font-semibold text-slate-700">{post.totalPosts || "—"}</span>
      </td>
      <td className="px-4 py-3 text-center hidden md:table-cell">
        <span className="text-sm text-slate-600">{post.lastDate || "Check Notification"}</span>
      </td>
      <td className="px-4 py-3 text-center">
        <StatusBadge publishedAt={post.publishedAt} lastDate={post.lastDate} />
      </td>
    </tr>
  );
}
