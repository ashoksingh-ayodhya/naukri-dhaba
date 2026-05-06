import type { Metadata } from "next";
import Link from "next/link";
import { buildMetadata } from "@/lib/seo";
import { CATEGORIES } from "@/config/site";
import Breadcrumb from "@/components/ui/Breadcrumb";

export const metadata: Metadata = buildMetadata({
  title: "Government Jobs by Category",
  description: "Browse all government job categories — SSC, Railway, Banking, UPSC, Police, Defence, Teaching, PSU and more.",
  path: "/jobs/",
});

export default function JobsHubPage() {
  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <Breadcrumb crumbs={[{ label: "Home", href: "/" }, { label: "Jobs" }]} />
      <div className="mt-4 mb-8">
        <h1 className="font-heading text-2xl md:text-3xl font-bold text-slate-900 mb-1">
          Government Jobs by Category
        </h1>
        <p className="text-slate-500 text-sm">Browse all job categories</p>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
        {CATEGORIES.map((cat) => (
          <Link
            key={cat.slug}
            href={`/jobs/${cat.slug}/`}
            className="card p-5 hover:shadow-md transition-shadow group"
          >
            <div className="text-3xl mb-3">{cat.icon}</div>
            <div className="font-heading font-bold text-slate-900 group-hover:text-primary-900 transition-colors">
              {cat.label}
            </div>
            <div className="text-xs text-slate-500 mt-0.5">{cat.fullName}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}
