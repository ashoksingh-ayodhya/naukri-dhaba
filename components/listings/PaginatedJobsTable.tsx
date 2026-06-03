"use client";

import { useState, useCallback } from "react";
import Link from "next/link";
import JobRow from "./JobRow";
import MobileJobCard from "./MobileJobCard";
import type { ListingPost } from "@/lib/types";

const PAGE_SIZE = 30;

interface Props {
  posts: ListingPost[];
  title: string;
  showHeader?: boolean;
  viewAllHref?: string;
}

export default function PaginatedJobsTable({ posts, title, showHeader = true, viewAllHref }: Props) {
  const [page, setPage] = useState(0);

  const totalPages = Math.ceil(posts.length / PAGE_SIZE);
  const visible = posts.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const start = page * PAGE_SIZE + 1;
  const end = Math.min((page + 1) * PAGE_SIZE, posts.length);

  const goTo = useCallback((p: number) => {
    setPage(p);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

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
            {visible.map((post) => (
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
                {visible.map((post, i) => (
                  <JobRow key={post.slug} post={post} index={i} />
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination bar */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-slate-100 bg-slate-50">
              <span className="text-xs text-slate-500">
                Showing {start}–{end} of {posts.length}
              </span>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => goTo(page - 1)}
                  disabled={page === 0}
                  className="px-3 py-1.5 text-xs font-medium rounded border border-slate-200 text-slate-600 hover:bg-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  ← Prev
                </button>

                {/* Page numbers — show at most 5 around current page */}
                {Array.from({ length: totalPages }, (_, i) => i)
                  .filter((i) => i === 0 || i === totalPages - 1 || Math.abs(i - page) <= 2)
                  .reduce<(number | "…")[]>((acc, cur, idx, arr) => {
                    if (idx > 0 && cur - (arr[idx - 1] as number) > 1) acc.push("…");
                    acc.push(cur);
                    return acc;
                  }, [])
                  .map((item, i) =>
                    item === "…" ? (
                      <span key={`ellipsis-${i}`} className="px-1 text-xs text-slate-400">…</span>
                    ) : (
                      <button
                        key={item}
                        onClick={() => goTo(item as number)}
                        className={`w-8 h-8 text-xs font-medium rounded border transition-colors ${
                          item === page
                            ? "bg-primary-900 text-white border-primary-900"
                            : "border-slate-200 text-slate-600 hover:bg-white"
                        }`}
                      >
                        {(item as number) + 1}
                      </button>
                    )
                  )}

                <button
                  onClick={() => goTo(page + 1)}
                  disabled={page === totalPages - 1}
                  className="px-3 py-1.5 text-xs font-medium rounded border border-slate-200 text-slate-600 hover:bg-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  Next →
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
