export const dynamicParams = false;

import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getPost, getAllPostMeta } from "@/lib/content";
import { buildMetadata, buildJobJsonLd } from "@/lib/seo";
import { siteConfig, CATEGORIES } from "@/config/site";
import MarkdownContent from "@/components/ui/MarkdownContent";
import Breadcrumb from "@/components/ui/Breadcrumb";
import PostHeader from "@/components/detail/PostHeader";
import ImportantDates from "@/components/detail/ImportantDates";
import ApplicationFee from "@/components/detail/ApplicationFee";
import VacancyBreakdown from "@/components/detail/VacancyBreakdown";
import ImportantLinks from "@/components/detail/ImportantLinks";
import HowToApply from "@/components/detail/HowToApply";
import ShareButtons from "@/components/ui/ShareButtons";

interface Props {
  params: Promise<{ category: string; slug: string }>;
}

export function generateStaticParams() {
  const params: { category: string; slug: string }[] = [];
  for (const cat of CATEGORIES) {
    const posts = getAllPostMeta("job", cat.slug);
    for (const post of posts) {
      params.push({ category: cat.slug, slug: post.slug });
    }
  }
  return params;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { category, slug } = await params;
  const post = getPost("job", category, slug);
  if (!post) return {};
  const { frontmatter: fm } = post;
  return buildMetadata({
    title: fm.title,
    description:
      fm.shortDescription ||
      `${fm.title} — ${fm.totalPosts ? fm.totalPosts + " posts, " : ""}Last Date: ${fm.lastDate || "Check Notification"}. Apply online at ${siteConfig.name}.`,
    path: `/jobs/${category}/${slug}/`,
  });
}

export default async function JobDetailPage({ params }: Props) {
  const { category, slug } = await params;
  const post = getPost("job", category, slug);
  if (!post) notFound();

  const { frontmatter: fm, content } = post;
  const cat = CATEGORIES.find((c) => c.slug === category);
  const pageUrl = `${siteConfig.url}/jobs/${category}/${slug}/`;
  const jsonLd = buildJobJsonLd(fm, pageUrl);

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <div className="max-w-7xl mx-auto px-4 py-6">
        <Breadcrumb
          crumbs={[
            { label: "Home", href: "/" },
            { label: "Jobs", href: "/jobs/" },
            { label: cat?.label || category, href: `/jobs/${category}/` },
            { label: fm.title },
          ]}
        />

        <div className="mt-4 grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main content */}
          <div className="lg:col-span-2 space-y-0">
            <PostHeader fm={fm} />

            {fm.shortDescription && (
              <div className="card p-5 mb-4">
                <p className="text-slate-700 leading-relaxed">{fm.shortDescription}</p>
              </div>
            )}

            <ImportantDates fm={fm} />
            <ApplicationFee fm={fm} />

            {fm.qualificationItems && fm.qualificationItems.length > 0 && (
              <div className="card mb-4">
                <div className="px-4 py-3 border-b border-slate-100">
                  <h2 className="section-title">🎓 Eligibility / Qualification</h2>
                </div>
                <ul className="px-4 py-4 space-y-2">
                  {fm.qualificationItems.map((item, i) => (
                    <li key={i} className="flex gap-2 text-sm text-slate-700">
                      <span className="text-green-500 shrink-0">✓</span>
                      {item}
                    </li>
                  ))}
                </ul>
                {fm.ageRelaxationNotes && (
                  <div className="px-4 pb-4 text-xs text-slate-500">
                    Age Relaxation: {fm.ageRelaxationNotes}
                  </div>
                )}
              </div>
            )}

            <VacancyBreakdown fm={fm} />

            {fm.salary && (
              <div className="card mb-4 p-4">
                <h2 className="section-title mb-2">💵 Salary / Pay Scale</h2>
                <p className="text-sm text-slate-700">{fm.salary}</p>
              </div>
            )}

            <HowToApply fm={fm} />
            <ImportantLinks fm={fm} />

            {content && content.trim() && (
              <div className="card p-5 mb-4 prose prose-sm max-w-none prose-headings:font-heading prose-a:text-primary-700">
                <MarkdownContent content={content} />
              </div>
            )}

            <div className="card p-4 mb-4">
              <ShareButtons title={fm.title} url={pageUrl} />
            </div>

            <p className="text-xs text-slate-400 mt-2">
              Source: Official Notification · Last updated: {fm.updatedAt || fm.publishedAt}
            </p>
          </div>

          {/* Sidebar */}
          <div className="space-y-4">
            {fm.applyUrl && fm.applyUrl !== "#" && (
              <div className="card p-5 sticky top-20">
                <h3 className="font-heading font-bold text-slate-900 mb-3">Quick Apply</h3>
                <a
                  href={`/go/?url=${encodeURIComponent(fm.applyUrl)}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-primary w-full justify-center"
                >
                  Apply Online ↗
                </a>
                {fm.lastDate && (
                  <p className="text-xs text-slate-500 mt-3 text-center">
                    Last Date: <span className="font-semibold text-red-600">{fm.lastDate}</span>
                  </p>
                )}
                {fm.notificationUrl && (
                  <a
                    href={fm.notificationUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn-secondary w-full justify-center mt-3"
                  >
                    Download Notification
                  </a>
                )}
              </div>
            )}

            <div className="card p-4">
              <h3 className="font-heading font-semibold text-slate-900 mb-3 text-sm">Quick Info</h3>
              <dl className="space-y-2 text-sm">
                {fm.organization && (
                  <div><dt className="text-slate-500 text-xs">Organization</dt><dd className="font-medium">{fm.organization}</dd></div>
                )}
                {fm.totalPosts && (
                  <div><dt className="text-slate-500 text-xs">Total Vacancies</dt><dd className="font-medium">{fm.totalPosts}</dd></div>
                )}
                {fm.qualification && (
                  <div><dt className="text-slate-500 text-xs">Qualification</dt><dd className="font-medium">{fm.qualification}</dd></div>
                )}
                {fm.salary && (
                  <div><dt className="text-slate-500 text-xs">Salary</dt><dd className="font-medium">{fm.salary}</dd></div>
                )}
              </dl>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
