import type { Metadata } from "next";
import { getAllPosts } from "@/lib/content";
import { buildMetadata } from "@/lib/seo";
import JobsTable from "@/components/listings/JobsTable";
import FilterBar from "@/components/listings/FilterBar";
import Breadcrumb from "@/components/ui/Breadcrumb";

export const metadata: Metadata = buildMetadata({
  title: "Admit Card 2024 — Download Hall Tickets",
  description: "Download latest admit cards, hall tickets and call letters for SSC, Railway, Banking, UPSC and all government exams.",
  path: "/admit-cards/",
});

export default function AdmitCardsPage() {
  const posts = getAllPosts("admit");
  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <Breadcrumb crumbs={[{ label: "Home", href: "/" }, { label: "Admit Cards" }]} />
      <div className="mt-4 mb-6">
        <h1 className="font-heading text-2xl md:text-3xl font-bold text-slate-900 mb-1">Admit Card 2024</h1>
        <p className="text-slate-500 text-sm">{posts.length} admit cards available</p>
      </div>
      <FilterBar baseHref="/admit-cards/" activeCategory={undefined} />
      <JobsTable posts={posts} title="All Admit Cards" showHeader={false} />
    </div>
  );
}
