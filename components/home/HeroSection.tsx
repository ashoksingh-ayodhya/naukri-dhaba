import Link from "next/link";
import { CATEGORIES } from "@/config/site";

interface HeroProps {
  jobCount: number;
  todayCount: number;
}

export default function HeroSection({ jobCount, todayCount }: HeroProps) {
  return (
    <section className="bg-gradient-to-br from-primary-900 via-primary-800 to-primary-950 text-white py-12 md:py-16">
      <div className="max-w-4xl mx-auto px-4 text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 bg-accent-500/20 rounded-full text-accent-400 text-sm font-semibold mb-4">
          <span className="w-2 h-2 bg-accent-400 rounded-full animate-pulse" />
          {todayCount} new jobs posted today
        </div>

        <h1 className="font-heading text-3xl md:text-5xl font-bold mb-4 leading-tight">
          Find Your{" "}
          <span className="text-accent-400">Sarkari Naukri</span>
          <br className="hidden md:block" /> in One Place
        </h1>

        <p className="text-white/70 text-lg mb-8 max-w-2xl mx-auto">
          Latest government job notifications, exam results, admit cards and syllabus — all updated daily from official sources.
        </p>

        {/* Search bar */}
        <form action="/search/" method="get" className="flex gap-2 max-w-xl mx-auto mb-8">
          <input
            type="text"
            name="q"
            placeholder="Search SSC, Railway, Banking, UPSC jobs..."
            className="flex-1 px-4 py-3 rounded-lg text-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-accent-500"
          />
          <button
            type="submit"
            className="px-5 py-3 bg-accent-500 hover:bg-accent-600 text-white font-semibold rounded-lg text-sm transition-colors whitespace-nowrap"
          >
            Search
          </button>
        </form>

        {/* Popular category pills */}
        <div className="flex flex-wrap justify-center gap-2">
          {CATEGORIES.slice(0, 8).map((cat) => (
            <Link
              key={cat.slug}
              href={`/jobs/${cat.slug}/`}
              className="px-3 py-1.5 bg-white/10 hover:bg-white/20 rounded-full text-sm text-white/80 hover:text-white transition-colors"
            >
              {cat.label}
            </Link>
          ))}
        </div>

        {/* Stats */}
        <div className="mt-10 grid grid-cols-3 gap-4 max-w-sm mx-auto">
          <div>
            <div className="text-2xl font-heading font-bold text-accent-400">{jobCount.toLocaleString()}+</div>
            <div className="text-xs text-white/60 mt-0.5">Total Posts</div>
          </div>
          <div>
            <div className="text-2xl font-heading font-bold text-accent-400">Daily</div>
            <div className="text-xs text-white/60 mt-0.5">Updates</div>
          </div>
          <div>
            <div className="text-2xl font-heading font-bold text-accent-400">Free</div>
            <div className="text-xs text-white/60 mt-0.5">No Registration</div>
          </div>
        </div>
      </div>
    </section>
  );
}
