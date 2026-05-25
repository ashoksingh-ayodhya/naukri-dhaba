export const dynamicParams = false;

import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getAllPosts } from "@/lib/content";
import { buildMetadata, buildListingPageJsonLd } from "@/lib/seo";
import { CATEGORIES, siteConfig } from "@/config/site";
import JobsTable from "@/components/listings/JobsTable";
import FilterBar from "@/components/listings/FilterBar";
import Breadcrumb from "@/components/ui/Breadcrumb";

const YEAR = new Date().getFullYear();

interface Props {
  params: Promise<{ category: string }>;
}

export function generateStaticParams() {
  return CATEGORIES.map((cat) => ({ category: cat.slug }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { category } = await params;
  const cat = CATEGORIES.find((c) => c.slug === category);
  if (!cat) return {};
  return buildMetadata({
    title: `${cat.fullName} Jobs ${YEAR} — Latest Recruitment Notifications`,
    description: `Latest ${YEAR} ${cat.fullName} job notifications. Check vacancies, eligibility, last date and apply online for ${cat.label} government jobs.`,
    path: `/jobs/${cat.slug}/`,
  });
}

export default async function CategoryPage({ params }: Props) {
  const { category } = await params;
  const cat = CATEGORIES.find((c) => c.slug === category);
  if (!cat) notFound();

  const posts = getAllPosts("job", category);
  const _listUrl = `${siteConfig.url}/jobs/${category}/`;
  const _items = posts.slice(0, 50).map((p: {title: string; slug: string}) => ({
    name: p.title,
    url: `${siteConfig.url}/jobs/${category}/${p.slug}/`,
  }));

  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(buildListingPageJsonLd(`${cat?.fullName || category} Jobs ${YEAR}`, _listUrl, _items)) }} />
      <div className="max-w-7xl mx-auto px-4 py-6">
        <Breadcrumb
          crumbs={[
            { label: "Home", href: "/" },
            { label: "Jobs", href: "/jobs/" },
            { label: cat.label },
          ]}
        />

        <div className="mt-4 mb-6">
          <div className="flex items-center gap-3">
            <span className="text-4xl">{cat.icon}</span>
            <div>
              <h1 className="font-heading text-2xl md:text-3xl font-bold text-slate-900">
                {cat.fullName} Jobs
              </h1>
              <p className="text-slate-500 text-sm">{posts.length} notifications found</p>
            </div>
          </div>
        </div>

        <FilterBar baseHref="/jobs/" activeCategory={category} />

        <JobsTable posts={posts} title={`${cat.label} Jobs`} showHeader={false} />
      </div>
    </>
  );
}
