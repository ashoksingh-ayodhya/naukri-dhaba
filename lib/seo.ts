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

export function buildJobJsonLd(fm: PostFrontmatter, url: string): object {
  const ld: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "JobPosting",
    title: fm.title,
    description: fm.shortDescription || fm.title,
    hiringOrganization: {
      "@type": "Organization",
      name: fm.organization,
      sameAs: fm.officialWebsite || "",
    },
    jobLocation: {
      "@type": "Place",
      address: { "@type": "PostalAddress", addressCountry: "IN" },
    },
    url,
    datePosted: fm.publishedAt,
  };

  if (fm.lastDate) {
    const [dd, mm, yyyy] = fm.lastDate.split("/");
    if (dd && mm && yyyy) {
      ld.validThrough = `${yyyy}-${mm}-${dd}T23:59:59`;
    }
  }

  if (fm.totalPosts) {
    ld.totalJobOpenings = parseInt(fm.totalPosts.replace(/[^0-9]/g, "")) || undefined;
  }

  return ld;
}
