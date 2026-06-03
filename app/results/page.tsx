import type { Metadata } from "next";
import { getAllPosts } from "@/lib/content";
import { buildMetadata } from "@/lib/seo";
import PaginatedJobsTable from "@/components/listings/PaginatedJobsTable";
import FilterBar from "@/components/listings/FilterBar";
import Breadcrumb from "@/components/ui/Breadcrumb";

const YEAR = new Date().getFullYear();

export const metadata: Metadata = buildMetadata({
  title: `Sarkari Result ${YEAR} — Latest Exam Results`,
  description: `Check ${YEAR} government exam results, merit lists, cut-off marks and scorecards. SSC, Railway, Banking, UPSC, Police results updated daily on Naukri Dhaba.`,
  path: "/results/",
});

export default function ResultsPage() {
  const posts = getAllPosts("result");
  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <Breadcrumb crumbs={[{ label: "Home", href: "/" }, { label: "Sarkari Result" }]} />
      <div className="mt-4 mb-6">
        <h1 className="font-heading text-2xl md:text-3xl font-bold text-slate-900 mb-1">Sarkari Result {YEAR}</h1>
        <h2 className="text-base font-semibold text-slate-700 mt-1 mb-1">
          Latest Government Exam Results {YEAR} — Merit Lists &amp; Cut-off Marks
        </h2>
        <p className="text-slate-500 text-sm">{posts.length} results available — updated daily</p>
      </div>
      <FilterBar baseHref="/results/" activeCategory={undefined} />
      <PaginatedJobsTable posts={posts} title="All Results" showHeader={false} />
    </div>
  );
}
