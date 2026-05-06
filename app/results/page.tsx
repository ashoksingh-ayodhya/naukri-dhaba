import type { Metadata } from "next";
import { getAllPosts } from "@/lib/content";
import { buildMetadata } from "@/lib/seo";
import JobsTable from "@/components/listings/JobsTable";
import FilterBar from "@/components/listings/FilterBar";
import Breadcrumb from "@/components/ui/Breadcrumb";

export const metadata: Metadata = buildMetadata({
  title: "Sarkari Result 2024 — Latest Exam Results",
  description: "Check latest government exam results, merit lists and scorecards. SSC, Railway, Banking, UPSC results updated daily.",
  path: "/results/",
});

export default function ResultsPage() {
  const posts = getAllPosts("result");
  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <Breadcrumb crumbs={[{ label: "Home", href: "/" }, { label: "Results" }]} />
      <div className="mt-4 mb-6">
        <h1 className="font-heading text-2xl md:text-3xl font-bold text-slate-900 mb-1">Sarkari Result 2024</h1>
        <p className="text-slate-500 text-sm">{posts.length} results available</p>
      </div>
      <FilterBar baseHref="/results/" activeCategory={undefined} />
      <JobsTable posts={posts} title="All Results" showHeader={false} />
    </div>
  );
}
