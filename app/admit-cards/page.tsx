import type { Metadata } from "next";
import { getAllPosts } from "@/lib/content";
import { buildMetadata } from "@/lib/seo";
import PaginatedJobsTable from "@/components/listings/PaginatedJobsTable";
import FilterBar from "@/components/listings/FilterBar";
import Breadcrumb from "@/components/ui/Breadcrumb";

const YEAR = new Date().getFullYear();

export const metadata: Metadata = buildMetadata({
  title: `Admit Card ${YEAR} — Download Hall Tickets`,
  description: `Download ${YEAR} admit cards, hall tickets and call letters for SSC, Railway, Banking, UPSC and all government exams. Get direct download links on Naukri Dhaba.`,
  path: "/admit-cards/",
});

export default function AdmitCardsPage() {
  const posts = getAllPosts("admit");
  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <Breadcrumb crumbs={[{ label: "Home", href: "/" }, { label: "Admit Cards" }]} />
      <div className="mt-4 mb-6">
        <h1 className="font-heading text-2xl md:text-3xl font-bold text-slate-900 mb-1">Admit Card {YEAR}</h1>
        <h2 className="text-base font-semibold text-slate-700 mt-1 mb-1">
          Download Latest Government Exam Admit Cards &amp; Hall Tickets {YEAR}
        </h2>
        <p className="text-slate-500 text-sm">{posts.length} admit cards available — direct download links</p>
      </div>
      <FilterBar baseHref="/admit-cards/" activeCategory={undefined} />
      <PaginatedJobsTable posts={posts} title="All Admit Cards" showHeader={false} />
    </div>
  );
}
