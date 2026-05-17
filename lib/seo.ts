import type { Metadata } from "next";
import { siteConfig } from "@/config/site";
import type { PostFrontmatter } from "./types";

export function buildMetadata({
  title,
  description,
  path: pagePath = "/",
  image,
  noindex,
}: {
  title: string;
  description: string;
  path?: string;
  image?: string;
  noindex?: boolean;
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
      images: [{ url: ogImage, width: 1200, height: 630, alt: `${title} | ${siteConfig.name}` }],
      locale: "en_IN",
      type: "website",
    },
    twitter: {
      card: "summary_large_image",
      title: `${title} | ${siteConfig.name}`,
      description,
      images: [{ url: ogImage, alt: `${title} | ${siteConfig.name}` }],
    },
    robots: noindex
      ? { index: false, follow: false }
      : { index: true, follow: true, googleBot: { index: true, follow: true } },
  };
}

function toIsoDate(raw: string | undefined): string | undefined {
  if (!raw) return undefined;
  if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw;
  // Extract DD/MM/YYYY from string — handles "13/02/2026 (Extended)" etc.
  const m = raw.match(/(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  if (m) return `${m[3]}-${m[2].padStart(2, "0")}-${m[1].padStart(2, "0")}`;
  return undefined;
}

function buildDescription(fm: PostFrontmatter): string {
  if (fm.shortDescription && fm.shortDescription.length > 60) return fm.shortDescription;
  const parts: string[] = [];
  const org = (fm.organization || fm.dept || "").trim();
  if (org) parts.push(`${org} has released a recruitment notification.`);
  if (fm.totalPosts) parts.push(`Total vacancies: ${fm.totalPosts} posts.`);
  if (fm.qualification) parts.push(`Eligibility: ${fm.qualification}.`);
  if (fm.applicationBegin && fm.lastDate)
    parts.push(`Apply: ${fm.applicationBegin} to ${fm.lastDate}.`);
  else if (fm.lastDate) parts.push(`Last date: ${fm.lastDate}.`);
  if (fm.salary) parts.push(`Pay scale: ${fm.salary}.`);
  if (fm.shortDescription) parts.unshift(fm.shortDescription);
  const desc = parts.join(" ").trim();
  return desc.length > 50
    ? desc
    : `${fm.title}. Government of India recruitment notification. Apply online at the official website.`;
}

export function buildJobJsonLd(fm: PostFrontmatter, url: string): object {
  const orgName =
    ((fm.organization || fm.dept || "Government of India").trim()) || "Government of India";
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
      address: { "@type": "PostalAddress", addressCountry: "IN", addressRegion: "India" },
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

export function buildBreadcrumbJsonLd(
  crumbs: Array<{ label: string; href?: string }>
): object {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: crumbs.map((crumb, i) => ({
      "@type": "ListItem",
      position: i + 1,
      name: crumb.label,
      ...(crumb.href ? { item: `${siteConfig.url}${crumb.href}` } : {}),
    })),
  };
}

export function buildWebSiteJsonLd(): object {
  return {
    "@context": "https://schema.org",
    "@type": "WebSite",
    url: siteConfig.url,
    name: siteConfig.name,
    description: siteConfig.description,
    inLanguage: "en-IN",
    potentialAction: {
      "@type": "SearchAction",
      target: { "@type": "EntryPoint", urlTemplate: `${siteConfig.url}/search/?q={search_term_string}` },
      "query-input": "required name=search_term_string",
    },
  };
}

export function buildOrganizationJsonLd(): object {
  return {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: siteConfig.name,
    url: siteConfig.url,
    logo: `${siteConfig.url}/logo.svg`,
    description: siteConfig.description,
    sameAs: [siteConfig.links.twitter, siteConfig.links.telegram],
  };
}
