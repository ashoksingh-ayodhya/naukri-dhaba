import type { Metadata } from "next";
import { siteConfig } from "@/config/site";
import type { PostFrontmatter } from "./types";

export function buildMetadata({
  title,
  description,
  path: pagePath = "/",
  image,
}: {
  title: string;
  description: string;
  path?: string;
  image?: string;
}): Metadata {
  const url = `${siteConfig.url}${pagePath}`;
  const ogImage = image || siteConfig.ogImage;

  return {
    title: { absolute: `${title} | ${siteConfig.name}` },
    description,
    metadataBase: new URL(siteConfig.url),
    alternates: { canonical: url },
    openGraph: {
      title: `${title} | ${siteConfig.name}`,
      description,
      url,
      siteName: siteConfig.name,
      images: [{ url: ogImage, width: 1200, height: 630, alt: title }],
      locale: "en_IN",
      type: "website",
    },
    twitter: {
      card: "summary_large_image",
      title: `${title} | ${siteConfig.name}`,
      description,
      images: [ogImage],
    },
    robots: {
      index: true,
      follow: true,
      googleBot: { index: true, follow: true },
    },
  };
}

function toIsoDate(raw: string | undefined): string | undefined {
  if (!raw) return undefined;
  // Already YYYY-MM-DD
  if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw;
  // Extract DD/MM/YYYY from string — handles "13/02/2026 (Extended)", "13/02/2026 Extended", etc.
  const m = raw.match(/(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  if (m) return `${m[3]}-${m[2].padStart(2, "0")}-${m[1].padStart(2, "0")}`;
  return undefined;
}

function buildDescription(fm: PostFrontmatter): string {
  const parts: string[] = [];
  const org = fm.organization || fm.dept;
  if (org) parts.push(`${org} has released a recruitment notification.`);
  if (fm.totalPosts) parts.push(`Total vacancies: ${fm.totalPosts} posts.`);
  if (fm.qualification) parts.push(`Eligibility: ${fm.qualification}.`);
  if (fm.applicationBegin && fm.lastDate)
    parts.push(`Application window: ${fm.applicationBegin} to ${fm.lastDate}.`);
  else if (fm.lastDate) parts.push(`Last date to apply: ${fm.lastDate}.`);
  if (fm.salary) parts.push(`Pay scale: ${fm.salary}.`);
  if (fm.howToApply && fm.howToApply.length > 0) parts.push(fm.howToApply[0]);
  if (fm.shortDescription) parts.unshift(fm.shortDescription);
  const desc = parts.join(" ").trim();
  // Google requires at least a meaningful sentence
  return desc.length > 50 ? desc : `${fm.title}. Government of India recruitment notification. Apply online at the official website.`;
}

export function buildJobJsonLd(fm: PostFrontmatter, url: string): object {
  // hiringOrganization.name must never be empty — critical GSC error
  const orgName = (fm.organization || fm.dept || "Government of India").trim() || "Government of India";

  const datePosted = toIsoDate(fm.publishedAt) || toIsoDate(fm.updatedAt) || "2026-01-01";

  const ld: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "JobPosting",
    title: fm.title,
    description: buildDescription(fm),
    hiringOrganization: {
      "@type": "Organization",
      name: orgName,
      ...(fm.officialWebsite ? { sameAs: fm.officialWebsite } : {}),
    },
    jobLocation: {
      "@type": "Place",
      address: { "@type": "PostalAddress", addressCountry: "IN" },
    },
    employmentType: "FULL_TIME",
    url,
    datePosted,
  };

  if (fm.lastDate) {
    const iso = toIsoDate(fm.lastDate);
    if (iso) ld.validThrough = `${iso}T23:59:59+05:30`;
  }

  const totalPosts = parseInt((fm.totalPosts || "").replace(/[^0-9]/g, ""));
  if (totalPosts > 0) ld.totalJobOpenings = totalPosts;

  if (fm.applyUrl && fm.applyUrl !== "#") ld.directApply = false;

  return ld;
}
