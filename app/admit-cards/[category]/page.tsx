export const dynamicParams = false;

import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getAllPosts } from "@/lib/content";
import { buildMetadata } from "@/lib/seo";
import { CATEGORIES } from "@/config/site";
import JobsTable from "@/components/listings/JobsTable";
import FilterBar from "@/components/listings/FilterBar";
import Breadcrumb from "@/components/ui/Breadcrumb";

interface Props { params: Promise<{ category: string }> }

export function generateStaticParams() {
  return CATEGORIES.map((cat) => ({ category: cat.slug }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { category } = await params;
  const cat = CATEGORIES.find((c) => c.slug === category);
  if (!cat) return {};
  return buildMetadata({
    title: `${cat.label} Admit Card 2024`,
    description: `Download latest ${cat.fullName} admit cards and hall tickets.`,
    path: `/admit-cards/${cat.slug}/`,
  });
}

export default async function AdmitCardCategoryPage({ params }: Props) {
  const { category } = await params;
  const cat = CATEGORIES.find((c) => c.slug === category);
  if (!cat) notFound();
  const posts = getAllPosts("admit", category);
  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <Breadcrumb crumbs={[{ label: "Home", href: "/" }, { label: "Admit Cards", href: "/admit-cards/" }, { label: cat.label }]} />
      <div className="mt-4 mb-6">
        <h1 className="font-heading text-2xl font-bold text-slate-900">{cat.label} Admit Card 2024</h1>
        <p className="text-slate-500 text-sm">{posts.length} admit cards found</p>
      </div>
      <FilterBar baseHref="/admit-cards/" activeCategory={category} />
      <JobsTable posts={posts} title={`${cat.label} Admit Cards`} showHeader={false} />
    </div>
  );
}
