export const dynamicParams = false;

import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getAllPosts } from "@/lib/content";
import { buildMetadata } from "@/lib/seo";
import { STATES } from "@/config/site";
import JobsTable from "@/components/listings/JobsTable";
import Breadcrumb from "@/components/ui/Breadcrumb";
import Link from "next/link";

interface Props { params: Promise<{ state: string }> }

export function generateStaticParams() {
  return STATES.map((s) => ({ state: s.slug }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { state: stateSlug } = await params;
  const state = STATES.find((s) => s.slug === stateSlug);
  if (!state) return {};
  return buildMetadata({
    title: `${state.label} Government Jobs`,
    description: `Latest ${state.label} (${state.abbr}) government jobs — state PSC, police, teaching and all state recruitment notifications.`,
    path: `/state/${state.slug}/`,
  });
}

export default async function StatePage({ params }: Props) {
  const { state: stateSlug } = await params;
  const state = STATES.find((s) => s.slug === stateSlug);
  if (!state) notFound();

  const allPosts = getAllPosts("job");
  const statePosts = allPosts.filter(
    (p) =>
      p.title.toLowerCase().includes(state.label.toLowerCase()) ||
      p.title.toLowerCase().includes(state.abbr.toLowerCase()) ||
      p.organization?.toLowerCase().includes(state.label.toLowerCase())
  );

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <Breadcrumb crumbs={[{ label: "Home", href: "/" }, { label: "State Jobs" }, { label: state.label }]} />
      <div className="mt-4 mb-6">
        <h1 className="font-heading text-2xl md:text-3xl font-bold text-slate-900 mb-1">
          {state.label} Government Jobs
        </h1>
        <p className="text-slate-500 text-sm">{statePosts.length} jobs found for {state.label}</p>
      </div>

      <div className="flex flex-wrap gap-2 mb-6">
        {STATES.map((s) => (
          <Link
            key={s.slug}
            href={`/state/${s.slug}/`}
            className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
              s.slug === stateSlug
                ? "bg-primary-900 text-white border-primary-900"
                : "bg-white text-slate-600 border-slate-200 hover:border-primary-300"
            }`}
          >
            {s.abbr}
          </Link>
        ))}
      </div>

      <JobsTable posts={statePosts} title={`${state.label} Jobs`} showHeader={false} />
    </div>
  );
}
