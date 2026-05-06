import type { Metadata } from "next";
import { getAllPosts } from "@/lib/content";
import { buildMetadata } from "@/lib/seo";
import JobsTable from "@/components/listings/JobsTable";
import FilterBar from "@/components/listings/FilterBar";
import Breadcrumb from "@/components/ui/Breadcrumb";

export const metadata: Metadata = buildMetadata({
  title: "Latest Government Jobs 2024",
  description:
    "Get latest Sarkari Naukri notifications — SSC, Railway, Banking, UPSC, Police, Defence jobs updated daily. Apply online for government jobs.",
  path: "/latest-jobs/",
});

export default function LatestJobsPage() {
  const posts = getAllPosts("job");

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <Breadcrumb crumbs={[{ label: "Home", href: "/" }, { label: "Latest Jobs" }]} />
      <div className="mt-4 mb-6">
        <h1 className="font-heading text-2xl md:text-3xl font-bold text-slate-900 mb-1">
          Latest Government Jobs
        </h1>
        <p className="text-slate-500 text-sm">{posts.length} job notifications available</p>
      </div>

      <FilterBar baseHref="/jobs/" activeCategory={undefined} />

      <JobsTable posts={posts} title="All Latest Jobs" showHeader={false} />
    </div>
  );
}
