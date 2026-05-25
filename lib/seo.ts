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

/** Parse "₹18,000 – ₹45,000 per month" → { min: 18000, max: 45000 } or null */
function parseSalaryRange(raw: string | undefined): { min: number; max: number } | null {
  if (!raw) return null;
  const nums = raw.replace(/[₹,\s]/g, "").match(/\d+/g);
  if (!nums || nums.length < 1) return null;
  const values = nums.map(Number).filter((n) => n >= 1000);
  if (values.length === 0) return null;
  return { min: values[0], max: values[values.length - 1] };
}

/** Map a qualification string to a schema.org credentialCategory */
function credentialCategory(qual: string | undefined): string {
  if (!qual) return "degree";
  const q = qual.toLowerCase();
  if (q.includes("10th") || q.includes("matriculation") || q.includes("sslc")) return "highschool";
  if (q.includes("12th") || q.includes("intermediate") || q.includes("hsc")) return "highschool";
  if (q.includes("diploma")) return "associate degree";
  if (q.includes("degree") || q.includes("graduate") || q.includes("b.sc") ||
      q.includes("b.a") || q.includes("b.com") || q.includes("b.e") || q.includes("b.tech")) return "bachelor degree";
  if (q.includes("post graduate") || q.includes("m.sc") || q.includes("m.a") ||
      q.includes("m.tech") || q.includes("mba")) return "postgraduate degree";
  return "degree";
}

export function buildJobJsonLd(fm: PostFrontmatter, url: string): object {
  const orgName = (fm.organization || fm.dept || "Government of India").trim() || "Government of India";
  const datePosted = toIsoDate(fm.publishedAt) || toIsoDate(fm.updatedAt) || "2026-01-01";

  const ld: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "JobPosting",
    title: fm.title,
    description: buildDescription(fm),
    url,
    datePosted,
    employmentType: "FULL_TIME",
    industry: "Government",
    occupationalCategory: "Government Services",
    hiringOrganization: {
      "@type": "Organization",
      name: orgName,
      sameAs: fm.officialWebsite || `https://www.google.com/search?q=${encodeURIComponent(orgName)}`,
    },
    jobLocation: {
      "@type": "Place",
      address: {
        "@type": "PostalAddress",
        addressCountry: "IN",
        addressRegion: "India",
      },
    },
    applicantLocationRequirements: {
      "@type": "Country",
      name: "India",
    },
  };

  // validThrough — last date to apply
  if (fm.lastDate) {
    const iso = toIsoDate(fm.lastDate);
    if (iso) ld.validThrough = `${iso}T23:59:59+05:30`;
  }

  // totalJobOpenings
  const totalPosts = parseInt((fm.totalPosts || "").replace(/[^0-9]/g, ""));
  if (totalPosts > 0) ld.totalJobOpenings = totalPosts;

  // baseSalary — parsed from salary string into MonetaryAmount
  const salaryRange = parseSalaryRange(fm.salary);
  if (salaryRange) {
    ld.baseSalary = {
      "@type": "MonetaryAmount",
      currency: "INR",
      value: {
        "@type": "QuantitativeValue",
        minValue: salaryRange.min,
        maxValue: salaryRange.max,
        unitText: "MONTH",
      },
    };
  }

  // educationRequirements
  if (fm.qualification) {
    ld.educationRequirements = {
      "@type": "EducationalOccupationalCredential",
      credentialCategory: credentialCategory(fm.qualification),
      competencyRequired: fm.qualification,
    };
  }

  // identifier — advertisement number
  if (fm.advertisementNo) {
    ld.identifier = {
      "@type": "PropertyValue",
      name: "Advertisement Number",
      value: fm.advertisementNo,
    };
  }

  // Age requirements as experienceRequirements
  if (fm.ageMin && fm.ageMax) {
    ld.experienceRequirements = {
      "@type": "OccupationalExperienceRequirements",
      monthsOfExperience: 0,
    };
    ld.applicantLocationRequirements = {
      "@type": "Country",
      name: "India",
    };
  }

  // directApply — false means candidates go to official site
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
    logo: {
      "@type": "ImageObject",
      url: `${siteConfig.url}/logo.svg`,
      width: 512,
      height: 512,
    },
    description: siteConfig.description,
    sameAs: [siteConfig.links.twitter, siteConfig.links.telegram],
  };
}

export function buildResultJsonLd(fm: PostFrontmatter, url: string): object {
  const orgName = (fm.organization || fm.dept || "Government of India").trim();
  const datePosted = toIsoDate(fm.publishedAt) || toIsoDate(fm.updatedAt) || "2026-01-01";
  return {
    "@context": "https://schema.org",
    "@type": "LearningResource",
    name: fm.title,
    description: buildDescription(fm),
    url,
    datePublished: datePosted,
    ...(fm.updatedAt ? { dateModified: toIsoDate(fm.updatedAt) || datePosted } : {}),
    provider: { "@type": "Organization", name: orgName },
    educationalLevel: "Government Exam",
    inLanguage: "en-IN",
    isAccessibleForFree: true,
  };
}

export function buildAdmitJsonLd(fm: PostFrontmatter, url: string): object {
  const orgName = (fm.organization || fm.dept || "Government of India").trim();
  const datePosted = toIsoDate(fm.publishedAt) || toIsoDate(fm.updatedAt) || "2026-01-01";
  const examDateIso = fm.examDate ? toIsoDate(fm.examDate) : undefined;
  return {
    "@context": "https://schema.org",
    "@type": "Event",
    name: fm.title,
    description: buildDescription(fm),
    url,
    startDate: examDateIso || datePosted,
    endDate: examDateIso || datePosted,
    image: `${siteConfig.url}${siteConfig.ogImage}`,
    eventStatus: "https://schema.org/EventScheduled",
    eventAttendanceMode: "https://schema.org/OfflineEventAttendanceMode",
    location: {
      "@type": "Place",
      name: "As per Admit Card",
      address: { "@type": "PostalAddress", addressCountry: "IN" },
    },
    organizer: { "@type": "Organization", name: orgName, url: fm.officialWebsite || siteConfig.url },
    offers: { "@type": "Offer", price: "0", priceCurrency: "INR", availability: "https://schema.org/InStock" },
  };
}

export function buildAnswerKeyJsonLd(fm: PostFrontmatter, url: string): object {
  const orgName = (fm.organization || fm.dept || "Government of India").trim();
  const datePosted = toIsoDate(fm.publishedAt) || "2026-01-01";
  return {
    "@context": "https://schema.org",
    "@type": "LearningResource",
    name: fm.title,
    description: buildDescription(fm),
    url,
    datePublished: datePosted,
    provider: { "@type": "Organization", name: orgName },
    educationalUse: "Answer Key",
    inLanguage: "en-IN",
    isAccessibleForFree: true,
  };
}

export function buildSyllabusJsonLd(fm: PostFrontmatter, url: string): object {
  const orgName = (fm.organization || fm.dept || "Government of India").trim();
  const datePosted = toIsoDate(fm.publishedAt) || "2026-01-01";
  return {
    "@context": "https://schema.org",
    "@type": "Course",
    name: fm.title,
    description: buildDescription(fm),
    url,
    datePublished: datePosted,
    provider: { "@type": "Organization", name: orgName },
    educationalLevel: "Government Exam Preparation",
    inLanguage: "en-IN",
    isAccessibleForFree: true,
    teaches: fm.qualification || "Government Exam Syllabus",
    hasCourseInstance: {
      "@type": "CourseInstance",
      courseMode: "online",
      instructor: { "@type": "Organization", name: orgName },
    },
  };
}

export function buildListingPageJsonLd(
  title: string,
  url: string,
  items: Array<{ name: string; url: string; description?: string }>
): object {
  return {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name: title,
    url,
    mainEntity: {
      "@type": "ItemList",
      itemListElement: items.slice(0, 50).map((item, i) => ({
        "@type": "ListItem",
        position: i + 1,
        name: item.name,
        url: item.url,
        ...(item.description ? { description: item.description } : {}),
      })),
    },
  };
}

export function buildFaqJsonLd(
  faqs: Array<{ question: string; answer: string }>
): object {
  return {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: faqs.map((faq) => ({
      "@type": "Question",
      name: faq.question,
      acceptedAnswer: { "@type": "Answer", text: faq.answer },
    })),
  };
}
