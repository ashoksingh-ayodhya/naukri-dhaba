import type { Metadata } from "next";
import { siteConfig } from "@/config/site";
import { getLatestByType, getLatestPosts } from "@/lib/content";
import HeroSection from "@/components/home/HeroSection";
import CategoryGrid from "@/components/home/CategoryGrid";
import LiveTicker from "@/components/home/LiveTicker";
import JobsTable from "@/components/listings/JobsTable";

export const metadata: Metadata = {
  title: `${siteConfig.name} — ${siteConfig.tagline}`,
  description: siteConfig.description,
};

export default function HomePage() {
  const latestJobs = getLatestPosts(50);
  const latestJobsOnly = getLatestByType("job", 30);
  const latestResults = getLatestByType("result", 20);
  const latestAdmits = getLatestByType("admit", 20);

  const todayStr = new Date().toISOString().split("T")[0];
  const todayCount = latestJobs.filter((p) => p.publishedAt >= todayStr).length;

  return (
    <>
      <LiveTicker posts={latestJobs.slice(0, 20)} />
      <HeroSection jobCount={latestJobs.length} todayCount={todayCount} />
      <CategoryGrid />

      <div className="max-w-7xl mx-auto px-4 pb-12">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main: Latest Jobs */}
          <div className="lg:col-span-2">
            <JobsTable
              posts={latestJobsOnly}
              title="🆕 Latest Government Jobs"
              viewAllHref="/latest-jobs/"
            />
          </div>

          {/* Sidebar: Results + Admit Cards */}
          <div className="space-y-6">
            <JobsTable
              posts={latestResults}
              title="📊 Latest Results"
              viewAllHref="/results/"
            />
            <JobsTable
              posts={latestAdmits}
              title="🪪 Admit Cards"
              viewAllHref="/admit-cards/"
            />
          </div>
        </div>
      </div>
    </>
  );
}
