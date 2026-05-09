import Link from 'next/link'
import JobRow from './JobRow'
import MobileJobCard from './MobileJobCard'
import type { ListingPost } from '@/lib/types'

interface JobsTableProps {
  posts: ListingPost[]
  title: string
  viewAllHref?: string
  showHeader?: boolean
}

export default function JobsTable({ posts, title, viewAllHref, showHeader = true }: JobsTableProps) {
  return (
    <div className="card">
      {showHeader && (
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
          <h2 className="section-title">{title}</h2>
          {viewAllHref && (
            <Link href={viewAllHref} className="text-sm text-primary-700 font-medium hover:underline">
              View All →
            </Link>
          )}
        </div>
      )}

      {posts.length === 0 ? (
        <p className="px-4 py-8 text-center text-slate-400 text-sm">No posts found.</p>
      ) : (
        <>
          {/* Mobile: card list */}
          <div className="sm:hidden divide-y divide-slate-100">
            {posts.map((post) => (
              <MobileJobCard key={post.slug} post={post} />
            ))}
          </div>

          {/* Desktop: table */}
          <div className="hidden sm:block overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="table-header">
                  <th className="px-4 py-2.5 text-left">Post Name</th>
                  <th className="px-4 py-2.5 text-center hidden sm:table-cell">Posts</th>
                  <th className="px-4 py-2.5 text-center hidden md:table-cell">Last Date</th>
                  <th className="px-4 py-2.5 text-center">Status</th>
                </tr>
              </thead>
              <tbody>
                {posts.map((post, i) => (
                  <JobRow key={post.slug} post={post} index={i} />
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
