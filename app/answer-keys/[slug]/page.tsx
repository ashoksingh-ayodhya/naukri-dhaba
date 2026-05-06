export const dynamicParams = false;

import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getPost, getAllPostMeta } from "@/lib/content";
import { buildMetadata } from "@/lib/seo";
import { siteConfig } from "@/config/site";
import MarkdownContent from "@/components/ui/MarkdownContent";
import Breadcrumb from "@/components/ui/Breadcrumb";
import PostHeader from "@/components/detail/PostHeader";
import ImportantLinks from "@/components/detail/ImportantLinks";
import ShareButtons from "@/components/ui/ShareButtons";

interface Props { params: Promise<{ slug: string }> }

export function generateStaticParams() {
  return getAllPostMeta("answer-key").map((p) => ({ slug: p.slug }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const post = getPost("answer-key", "", slug);
  if (!post) return {};
  const { frontmatter: fm } = post;
  return buildMetadata({
    title: `${fm.title} Answer Key`,
    description: fm.shortDescription || `Download official answer key for ${fm.title}.`,
    path: `/answer-keys/${slug}/`,
  });
}

export default async function AnswerKeyDetailPage({ params }: Props) {
  const { slug } = await params;
  const post = getPost("answer-key", "", slug);
  if (!post) notFound();
  const { frontmatter: fm, content } = post;
  const pageUrl = `${siteConfig.url}/answer-keys/${slug}/`;

  return (
    <div className="max-w-5xl mx-auto px-4 py-6">
      <Breadcrumb crumbs={[{ label: "Home", href: "/" }, { label: "Answer Keys", href: "/answer-keys/" }, { label: fm.title }]} />
      <div className="mt-4 space-y-4">
        <PostHeader fm={fm} />
        {fm.shortDescription && <div className="card p-5"><p className="text-slate-700 leading-relaxed">{fm.shortDescription}</p></div>}
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
