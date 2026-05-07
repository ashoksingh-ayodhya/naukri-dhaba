import Link from 'next/link'
import { StatusBadge, CategoryBadge } from '@/components/ui/Badge'
import { isExpired } from '@/lib/content'
import type { ListingPost } from '@/lib/types'

export default function MobileJobCard({ post }: { post: ListingPost }) {
  const expired = isExpired(post.lastDate)
  return (
    <Link
      href={post.href}
      className="flex items-start gap-3 px-4 py-3.5 hover:bg-slate-50 active:bg-slate-100 transition-colors"
    >
      {/* Status stripe */}
      <div
        className={`w-1 self-stretch rounded-full shrink-0 mt-0.5 ${
          expired ? 'bg-slate-300' : 'bg-green-400'
        }`}
      />

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className="text-[13px] font-semibold text-slate-800 leading-snug line-clamp-2">
          {post.title}
        </p>
        <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 mt-1.5">
          <CategoryBadge category={post.category} dept={post.dept} />
          {post.totalPosts && (
            <span className="text-[11px] text-slate-500">
              {post.totalPosts} Posts
            </span>
          )}
          {post.lastDate && (
            <span className="text-[11px] text-slate-400">
              · Last: {post.lastDate}
            </span>
          )}
        </div>
      </div>

      {/* Status badge */}
      <div className="shrink-0 mt-0.5">
        <StatusBadge publishedAt={post.publishedAt} lastDate={post.lastDate} />
      </div>
    </Link>
  )
}
