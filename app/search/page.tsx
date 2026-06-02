import type { Metadata } from "next";
import { Suspense } from "react";
import { buildMetadata } from "@/lib/seo";
import Breadcrumb from "@/components/ui/Breadcrumb";
import SearchClient from "./SearchClient";

export const metadata: Metadata = buildMetadata({
  title: `Search Government Jobs — SSC, Railway, Banking, UPSC ${new Date().getFullYear()}`,
  description:
    "Search across latest government job notifications, results, admit cards and syllabi from SSC, Railway, Banking, UPSC, Police and all state govt bodies.",
  path: "/search/",
});

export default function SearchPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      <Breadcrumb crumbs={[{ label: "Home", href: "/" }, { label: "Search" }]} />
      <Suspense
        fallback={
          <div className="py-8 text-center text-slate-400">Loading search...</div>
        }
      >
        <SearchClient />
      </Suspense>
    </div>
  );
}
