import type { Metadata } from "next";
import { getAllPosts } from "@/lib/content";
import { buildMetadata } from "@/lib/seo";
import JobsTable from "@/components/listings/JobsTable";
import FilterBar from "@/components/listings/FilterBar";
import Breadcrumb from "@/components/ui/Breadcrumb";

const YEAR = new Date().getFullYear();

export const metadata: Metadata = buildMetadata({
  title: `Latest Government Jobs ${YEAR} — Sarkari Naukri`,
  description: `${YEAR} government job notifications — SSC, Railway, Banking, UPSC, Police, Defence updated daily. Check eligibility, last date and apply online for latest Sarkari Naukri.`,
  path: "/latest-jobs/",
});

export default function LatestJobsPage() {
  const posts = getAllPosts("job");

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <Breadcrumb crumbs={[{ label: "Home", href: "/" }, { label: "Latest Government Jobs" }]} />
      <div className="mt-4 mb-6">
        <h1 className="font-heading text-2xl md:text-3xl font-bold text-slate-900 mb-1">
          Latest Government Jobs {YEAR}
        </h1>
        <h2 className="text-base font-semibold text-slate-700 mt-1 mb-1">
          Latest Central &amp; State Government Job Notifications {YEAR}
        </h2>
        <p className="text-slate-500 text-sm">
          Active &amp; upcoming vacancies — updated daily. {posts.filter(p => !p.lastDate || new Date(p.lastDate.split('/').reverse().join('-')) >= new Date()).length} active, {posts.length} total.
        </p>
      </div>

      <FilterBar baseHref="/jobs/" activeCategory={undefined} />

      <JobsTable posts={posts} title="All Latest Jobs" showHeader={false} />
    </div>
  );
}
