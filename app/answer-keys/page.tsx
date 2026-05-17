import type { Metadata } from "next";
import { getAllPosts } from "@/lib/content";
import { buildMetadata } from "@/lib/seo";
import JobsTable from "@/components/listings/JobsTable";
import Breadcrumb from "@/components/ui/Breadcrumb";

const YEAR = new Date().getFullYear();

export const metadata: Metadata = buildMetadata({
  title: `Answer Key ${YEAR} — Official Government Exam Answer Keys`,
  description: `Download official ${YEAR} answer keys for SSC, Railway, Banking, UPSC and all government exams. Check your score against provisional and final answer keys before results are declared.`,
  path: "/answer-keys/",
});

export default function AnswerKeysPage() {
  const posts = getAllPosts("answer-key");
  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <Breadcrumb crumbs={[{ label: "Home", href: "/" }, { label: "Answer Keys" }]} />
      <div className="mt-4 mb-6">
        <h1 className="font-heading text-2xl md:text-3xl font-bold text-slate-900 mb-1">Answer Key {YEAR}</h1>
        <p className="text-slate-500 text-sm">{posts.length} answer keys available</p>
      </div>
      <JobsTable posts={posts} title="All Answer Keys" showHeader={false} />
    </div>
  );
}
