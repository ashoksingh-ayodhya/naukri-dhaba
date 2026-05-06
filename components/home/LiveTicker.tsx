import Link from "next/link";
import type { ListingPost } from "@/lib/types";

export default function LiveTicker({ posts }: { posts: ListingPost[] }) {
  if (!posts.length) return null;

  const items = [...posts, ...posts]; // duplicate for seamless loop

  return (
    <div className="bg-primary-900 text-white border-b border-primary-950">
      <div className="max-w-7xl mx-auto px-4 flex items-center h-9 overflow-hidden">
        <span className="shrink-0 text-xs font-bold text-accent-400 uppercase tracking-wider pr-3 border-r border-white/20 mr-3">
          🔴 Live
        </span>
        <div className="overflow-hidden flex-1">
          <div className="ticker-inner flex gap-8 whitespace-nowrap">
            {items.map((post, i) => (
              <Link
                key={`${post.slug}-${i}`}
                href={post.href}
                className="text-xs text-white/80 hover:text-white transition-colors shrink-0"
              >
                <span className="text-accent-400 mr-1">▸</span>
                {post.title}
                {post.lastDate && (
                  <span className="text-white/50 ml-1">· Last Date: {post.lastDate}</span>
                )}
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
