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
      site: "@naukridhaba",
      creator: "@naukridhaba",
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
  // Accept both DD/MM/YYYY and DD-MM-YYYY separators — handles "13/02/2026 (Extended)" etc.
  const m = raw.match(/(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})/);
  if (m) return `${m[3]}-${m[2].padStart(2, "0")}-${m[1].padStart(2, "0")}`;
  return undefined;
}

function buildDescription(fm: PostFrontmatter): string {
  // If shortDescription exists and is within the ideal 60-160 char range, use it as-is
  if (fm.shortDescription && fm.shortDescription.length >= 60 && fm.shortDescription.length <= 160)
    return fm.shortDescription;
  // If shortDescription is > 160 chars, truncate it
  if (fm.shortDescription && fm.shortDescription.length > 160)
    return fm.shortDescription.slice(0, 157) + "...";
  // Build from parts (shortDescription < 60 chars or missing)
  const parts: string[] = [];
  const org = (fm.organization || fm.dept || "").trim();
  if (org) parts.push(`${org} has released a recruitment notification.`);
  if (fm.totalPosts) parts.push(`Total vacancies: ${fm.totalPosts} posts.`);
  if (fm.qualification) parts.push(`Eligibility: ${fm.qualification}.`);
  if (fm.applicationBegin && fm.lastDate)
    parts.push(`Apply: ${fm.applicationBegin} to ${fm.lastDate}.`);
  else if (fm.lastDate) parts.push(`Last date: ${fm.lastDate}.`);
  if (fm.salary) parts.push(`Pay scale: ${fm.salary}.`);
  // Prepend short shortDescription if it exists but was < 60 chars
  if (fm.shortDescription) parts.unshift(fm.shortDescription);
  const desc = parts.join(" ").trim();
  const result = desc.length > 50
    ? desc
    : `${fm.title}. Government of India recruitment notification. Apply online at the official website.`;
  // Ensure final output is ≤ 160 chars
  return result.length > 160 ? result.slice(0, 157) + "..." : result;
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

/** Map a qualification string to a valid schema.org/Google JobPosting credentialCategory enum value */
function credentialCategory(qual: string | undefined): string | null {
  if (!qual) return null;
  const q = qual.toLowerCase();
  if (q.includes("10th") || q.includes("matriculation") || q.includes("sslc")) return "high school";
  if (q.includes("12th") || q.includes("intermediate") || q.includes("hsc")) return "high school";
  if (q.includes("diploma")) return "associate degree";
  if (q.includes("degree") || q.includes("graduate") || q.includes("b.sc") ||
      q.includes("b.a") || q.includes("b.com") || q.includes("b.e") || q.includes("b.tech")) return "bachelor degree";
  if (q.includes("post graduate") || q.includes("m.sc") || q.includes("m.a") ||
      q.includes("m.tech") || q.includes("mba")) return "postgraduate degree";
  return null;
}

/** Derive a valid Indian state addressRegion from the hiring org name. */
function inferRegion(orgName: string): string {
  const o = orgName.toLowerCase();
  if (o.includes("madhya pradesh") || o.includes("mppsc")) return "Madhya Pradesh";
  if (o.includes("uttar pradesh") || o.includes("uppsc") || o.includes("upsssc")) return "Uttar Pradesh";
  if (o.includes("rajasthan") || o.includes("rpsc") || o.includes("rsmssb")) return "Rajasthan";
  if (o.includes("bihar") || o.includes("bpsc") || o.includes("bssc")) return "Bihar";
  if (o.includes("gujarat") || o.includes("gpsc")) return "Gujarat";
  if (o.includes("maharashtra") || o.includes("mpsc")) return "Maharashtra";
  if (o.includes("karnataka") || o.includes("kpsc")) return "Karnataka";
  if (o.includes("tamil nadu") || o.includes("tnpsc")) return "Tamil Nadu";
  if (o.includes("andhra pradesh") || o.includes("appsc")) return "Andhra Pradesh";
  if (o.includes("telangana") || o.includes("tspsc")) return "Telangana";
  if (o.includes("kerala")) return "Kerala";
  if (o.includes("west bengal") || o.includes("wbpsc") || o.includes("wbssc")) return "West Bengal";
  if (o.includes("punjab") || o.includes("ppsc")) return "Punjab";
  if (o.includes("haryana") || o.includes("hpsc") || o.includes("hssc")) return "Haryana";
  if (o.includes("himachal") || o.includes("hppsc")) return "Himachal Pradesh";
  if (o.includes("jharkhand") || o.includes("jpsc") || o.includes("jssc")) return "Jharkhand";
  if (o.includes("odisha") || o.includes("opsc") || o.includes("ossc")) return "Odisha";
  if (o.includes("chhattisgarh") || o.includes("cgpsc") || o.includes("cgvyapam")) return "Chhattisgarh";
  if (o.includes("assam") || o.includes("apsc") || o.includes("slrc")) return "Assam";
  if (o.includes("uttarakhand") || o.includes("ukpsc") || o.includes("uksssc")) return "Uttarakhand";
  return "Delhi";
}

/** Derive a valid addressLocality from the hiring org name (for state PSC jobs). */
function inferLocality(orgName: string): string {
  const o = orgName.toLowerCase();
  if (o.includes("madhya pradesh") || o.includes("mppsc")) return "Bhopal";
  if (o.includes("uttar pradesh") || o.includes("uppsc") || o.includes("upsssc")) return "Lucknow";
  if (o.includes("rajasthan") || o.includes("rpsc") || o.includes("rsmssb")) return "Jaipur";
  if (o.includes("bihar") || o.includes("bpsc") || o.includes("bssc")) return "Patna";
  if (o.includes("gujarat") || o.includes("gpsc")) return "Gandhinagar";
  if (o.includes("maharashtra") || o.includes("mpsc")) return "Mumbai";
  if (o.includes("karnataka") || o.includes("kpsc")) return "Bengaluru";
  if (o.includes("tamil nadu") || o.includes("tnpsc")) return "Chennai";
  if (o.includes("andhra pradesh") || o.includes("appsc")) return "Amaravati";
  if (o.includes("telangana") || o.includes("tspsc")) return "Hyderabad";
  if (o.includes("kerala") || o.includes("kerala psc")) return "Thiruvananthapuram";
  if (o.includes("west bengal") || o.includes("wbpsc") || o.includes("wbssc")) return "Kolkata";
  if (o.includes("punjab") || o.includes("ppsc")) return "Chandigarh";
  if (o.includes("haryana") || o.includes("hpsc") || o.includes("hssc")) return "Chandigarh";
  if (o.includes("himachal") || o.includes("hppsc")) return "Shimla";
  if (o.includes("jharkhand") || o.includes("jpsc") || o.includes("jssc")) return "Ranchi";
  if (o.includes("odisha") || o.includes("opsc") || o.includes("ossc")) return "Bhubaneswar";
  if (o.includes("chhattisgarh") || o.includes("cgpsc") || o.includes("cgvyapam")) return "Raipur";
  if (o.includes("assam") || o.includes("apsc") || o.includes("slrc")) return "Guwahati";
  if (o.includes("uttarakhand") || o.includes("ukpsc") || o.includes("uksssc")) return "Dehradun";
  return "New Delhi";
}

const MAJOR_ORG_URLS: Record<string, string> = {
  "Staff Selection Commission": "https://ssc.nic.in",
  "Railway Recruitment Board": "https://www.rrbcdg.gov.in",
  "Union Public Service Commission": "https://upsc.gov.in",
  "Institute of Banking Personnel Selection": "https://www.ibps.in",
  "State Bank of India": "https://www.sbi.co.in",
  "Reserve Bank of India": "https://www.rbi.org.in",
  "National Bank for Agriculture and Rural Development": "https://www.nabard.org",
  "Life Insurance Corporation": "https://www.licindia.in",
  "India Post": "https://www.indiapost.gov.in",
  "National Health Mission": "https://nhm.gov.in",
  "DRDO": "https://www.drdo.gov.in",
  "ISRO": "https://www.isro.gov.in",
  "AIIMS": "https://www.aiims.edu",
  "NTPC": "https://www.ntpc.co.in",
  "ONGC": "https://www.ongcindia.com",
};

export function buildJobJsonLd(fm: PostFrontmatter, url: string): object {
  const orgName = (fm.organization || fm.dept || "Government of India").trim() || "Government of India";
  const datePosted = toIsoDate(fm.publishedAt) || toIsoDate(fm.updatedAt) || "2026-01-01";

  // Prefer major org canonical URL, then fall back to fm.officialWebsite if it's a real URL
  const orgUrl = MAJOR_ORG_URLS[fm.organization || ""] ||
    (fm.officialWebsite && fm.officialWebsite.startsWith("http") ? fm.officialWebsite : undefined);

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
      ...(orgUrl ? { sameAs: orgUrl } : {}),
    },
    // jobLocation uses a real city + state (inferred from org name) — "India" is NOT a valid addressRegion
    jobLocation: {
      "@type": "Place",
      address: {
        "@type": "PostalAddress",
        addressLocality: inferLocality(orgName),
        addressRegion: inferRegion(orgName),
        addressCountry: "IN",
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

  // educationRequirements — only set credentialCategory when it maps to a valid enum value
  if (fm.qualification) {
    const category = credentialCategory(fm.qualification);
    ld.educationRequirements = {
      "@type": "EducationalOccupationalCredential",
      ...(category ? { credentialCategory: category } : {}),
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

  // Note: age limits are NOT work experience — no experienceRequirements mapping.
  // monthsOfExperience must be a positive number per Google's spec; age has no valid mapping here.

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
    "@type": "NewsArticle",
    headline: fm.title,
    description: buildDescription(fm),
    url,
    datePublished: datePosted,
    dateModified: toIsoDate(fm.updatedAt) || datePosted,
    author: { "@type": "Organization", name: siteConfig.name, url: siteConfig.url },
    publisher: {
      "@type": "Organization",
      name: siteConfig.name,
      url: siteConfig.url,
      logo: { "@type": "ImageObject", url: `${siteConfig.url}/logo.svg`, width: 512, height: 512 },
    },
    image: `${siteConfig.url}${siteConfig.ogImage}`,
    inLanguage: "en-IN",
    about: { "@type": "Organization", name: orgName },
  };
}

export function buildAdmitJsonLd(fm: PostFrontmatter, url: string): object {
  const orgName = (fm.organization || fm.dept || "Government of India").trim();
  const datePosted = toIsoDate(fm.publishedAt) || toIsoDate(fm.updatedAt) || "2026-01-01";
  return {
    "@context": "https://schema.org",
    "@type": "NewsArticle",
    headline: fm.title,
    description: buildDescription(fm),
    url,
    datePublished: datePosted,
    dateModified: toIsoDate(fm.updatedAt) || datePosted,
    author: { "@type": "Organization", name: siteConfig.name, url: siteConfig.url },
    publisher: {
      "@type": "Organization",
      name: siteConfig.name,
      url: siteConfig.url,
      logo: { "@type": "ImageObject", url: `${siteConfig.url}/logo.svg`, width: 512, height: 512 },
    },
    image: `${siteConfig.url}${siteConfig.ogImage}`,
    inLanguage: "en-IN",
    about: { "@type": "Organization", name: orgName },
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

/** Generate up to 4 default FAQs from frontmatter when no FAQ content is found in the post body. */
export function buildDefaultFaqs(fm: PostFrontmatter): Array<{ question: string; answer: string }> {
  const faqs: Array<{ question: string; answer: string }> = [];
  if (fm.lastDate)
    faqs.push({ question: `What is the last date to apply for ${fm.title}?`, answer: `The last date to apply is ${fm.lastDate}.` });
  if (fm.totalPosts)
    faqs.push({ question: `How many vacancies are available in ${fm.organization || fm.title}?`, answer: `There are ${fm.totalPosts} vacancies.` });
  if (fm.qualification)
    faqs.push({ question: `What is the eligibility/qualification for ${fm.title}?`, answer: fm.qualification });
  if (fm.salary)
    faqs.push({ question: `What is the salary for this post?`, answer: fm.salary });
  return faqs.slice(0, 4);
}

/** HowTo schema for how-to-apply steps — replaces deprecated FAQPage (dead since May 7 2026) */
export function buildHowToJsonLd(
  title: string,
  steps: string[],
  url: string
): object {
  return {
    "@context": "https://schema.org",
    "@type": "HowTo",
    name: `How to Apply for ${title}`,
    description: `Step-by-step guide to apply for ${title} government job.`,
    url,
    step: steps.map((text, i) => ({
      "@type": "HowToStep",
      position: i + 1,
      name: text.length > 60 ? text.slice(0, 57) + "…" : text,
      text,
    })),
  };
}
