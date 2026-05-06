export const dynamicParams = false;

import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getPost, getAllPostMeta } from "@/lib/content";
import { buildMetadata } from "@/lib/seo";
import { siteConfig, CATEGORIES } from "@/config/site";
import MarkdownContent from "@/components/ui/MarkdownContent";
import Breadcrumb from "@/components/ui/Breadcrumb";
import PostHeader from "@/components/detail/PostHeader";
import ImportantDates from "@/components/detail/ImportantDates";
import ImportantLinks from "@/components/detail/ImportantLinks";
import ShareButtons from "@/components/ui/ShareButtons";

interface Props { params: Promise<{ category: string; slug: string }> }

export function generateStaticParams() {
  const params: { category: string; slug: string }[] = [];
  for (const cat of CATEGORIES) {
    const posts = getAllPostMeta("result", cat.slug);
    for (const post of posts) {
      params.push({ category: cat.slug, slug: post.slug });
    }
  }
  return params;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { category, slug } = await params;
  const post = getPost("result", category, slug);
  if (!post) return {};
  const { frontmatter: fm } = post;
  return buildMetadata({
    title: fm.title,
    description: fm.shortDescription || `${fm.title} result declared. Check merit list and scorecard.`,
    path: `/results/${category}/${slug}/`,
  });
}

export default async function ResultDetailPage({ params }: Props) {
  const { category, slug } = await params;
  const post = getPost("result", category, slug);
  if (!post) notFound();
  const { frontmatter: fm, content } = post;
  const cat = CATEGORIES.find((c) => c.slug === category);
  const pageUrl = `${siteConfig.url}/results/${category}/${slug}/`;

  return (
    <div className="max-w-5xl mx-auto px-4 py-6">
      <Breadcrumb crumbs={[{ label: "Home", href: "/" }, { label: "Results", href: "/results/" }, { label: cat?.label || category, href: `/results/${category}/` }, { label: fm.title }]} />
      <div className="mt-4 space-y-4">
        <PostHeader fm={fm} />
        {fm.shortDescription && <div className="card p-5"><p className="text-slate-700 leading-relaxed">{fm.shortDescription}</p></div>}
        <ImportantDates fm={fm} />
        <ImportantLinks fm={fm} />
        {content?.trim() && (
          <div className="card p-5 prose prose-sm max-w-none prose-headings:font-heading">
            <MarkdownContent content={content} />
          </div>
        )}
        <div className="card p-4"><ShareButtons title={fm.title} url={pageUrl} /></div>
      </div>
    </div>
  );
}
