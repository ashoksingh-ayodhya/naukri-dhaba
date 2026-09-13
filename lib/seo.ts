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

const MONTHS: Record<string, string> = {
  jan: "01", feb: "02", mar: "03", apr: "04", may: "05", jun: "06",
  jul: "07", aug: "08", sep: "09", sept: "09", oct: "10", nov: "11", dec: "12",
};

/** DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD, "27 July 2026" or "July 27, 2026" → YYYY-MM-DD */
export function toIsoDate(raw: string | undefined): string | undefined {
  if (!raw) return undefined;
  let m = raw.match(/(\d{4})-(\d{2})-(\d{2})/);
  if (m) return `${m[1]}-${m[2]}-${m[3]}`;
  m = raw.match(/(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{4})/);
  if (m) return `${m[3]}-${m[2].padStart(2, "0")}-${m[1].padStart(2, "0")}`;
  m = raw.match(/(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3,9})\.?,?\s+(\d{4})/);
  if (m && MONTHS[m[2].slice(0, 3).toLowerCase()])
    return `${m[3]}-${MONTHS[m[2].slice(0, 3).toLowerCase()]}-${m[1].padStart(2, "0")}`;
  m = raw.match(/([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})/);
  if (m && MONTHS[m[1].slice(0, 3).toLowerCase()])
    return `${m[3]}-${MONTHS[m[1].slice(0, 3).toLowerCase()]}-${m[2].padStart(2, "0")}`;
  return undefined;
}

function esc(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function feeText(v: string | undefined): string {
  if (!v) return "";
  return /^\d+$/.test(v) ? `₹${Number(v).toLocaleString("en-IN")}` : v;
}

const GENERIC_DEPT = new Set(["GOVERNMENT", "GOVT", "POLICE", "DEFENCE", "TEACHING", "PSU", "STATE PSC", "POSTAL", "MEDICAL", "RAILWAY", "BANK", "BANKING"]);

function orgName(fm: PostFrontmatter): string {
  const org = (fm.organization || "").trim();
  if (org) return org;
  const dept = (fm.dept || "").trim();
  return GENERIC_DEPT.has(dept.toUpperCase()) ? "" : dept;
}

/** Plain-text summary used for Article-type schema descriptions (≤ 300 chars). */
function plainDescription(fm: PostFrontmatter): string {
  const parts: string[] = [];
  if (fm.shortDescription) parts.push(fm.shortDescription);
  if (fm.totalPosts) parts.push(`Total posts: ${fm.totalPosts}.`);
  if (fm.examDate) parts.push(`Exam date: ${fm.examDate}.`);
  const text = parts.join(" ").trim() || fm.title;
  return text.length > 300 ? text.slice(0, 297) + "..." : text;
}

/**
 * Google wants the JobPosting description to be the full posting in HTML —
 * responsibilities, eligibility, dates, fees — not a one-line teaser.
 */
export function buildJobDescriptionHtml(fm: PostFrontmatter): string {
  const blocks: string[] = [];
  if (fm.shortDescription) blocks.push(`<p>${esc(fm.shortDescription)}</p>`);

  const facts: string[] = [];
  const org = orgName(fm);
  if (org) facts.push(`<li><strong>Organisation:</strong> ${esc(org)}</li>`);
  if (fm.advertisementNo) facts.push(`<li><strong>Advertisement No.:</strong> ${esc(fm.advertisementNo)}</li>`);
  if (fm.totalPosts) facts.push(`<li><strong>Total posts:</strong> ${esc(fm.totalPosts)}</li>`);
  if (fm.applicationBegin) facts.push(`<li><strong>Application begins:</strong> ${esc(fm.applicationBegin)}</li>`);
  if (fm.lastDate) facts.push(`<li><strong>Last date to apply:</strong> ${esc(fm.lastDate)}</li>`);
  if (fm.examDate) facts.push(`<li><strong>Exam date:</strong> ${esc(fm.examDate)}</li>`);
  if (fm.qualification) facts.push(`<li><strong>Qualification:</strong> ${esc(fm.qualification)}</li>`);
  if (fm.ageMin || fm.ageMax) {
    const range = fm.ageMin && fm.ageMax ? `${fm.ageMin} to ${fm.ageMax} years` : fm.ageMax ? `up to ${fm.ageMax} years` : `${fm.ageMin} years and above`;
    facts.push(`<li><strong>Age limit:</strong> ${range}${fm.ageReferenceDate ? ` (as on ${esc(fm.ageReferenceDate)})` : ""}</li>`);
  }
  if (fm.feeGeneral) facts.push(`<li><strong>Application fee (General/OBC/EWS):</strong> ${esc(feeText(fm.feeGeneral))}</li>`);
  if (fm.feeSCST) facts.push(`<li><strong>Application fee (SC/ST/PwD):</strong> ${esc(feeText(fm.feeSCST))}</li>`);
  if (fm.salary) facts.push(`<li><strong>Pay scale:</strong> ${esc(fm.salary)}</li>`);
  if (facts.length) blocks.push(`<ul>${facts.join("")}</ul>`);

  if (fm.qualificationItems?.length)
    blocks.push(`<p><strong>Eligibility</strong></p><ul>${fm.qualificationItems.map((q) => `<li>${esc(q)}</li>`).join("")}</ul>`);
  if (fm.vacancyBreakdown?.length) {
    const rows = fm.vacancyBreakdown
      .slice(0, 30)
      .map((r) => `<li>${esc(r.post_name)}${r.total ? `: ${esc(r.total)} posts` : ""}${r.eligibility ? ` — ${esc(r.eligibility)}` : ""}</li>`)
      .join("");
    blocks.push(`<p><strong>Vacancy details</strong></p><ul>${rows}</ul>`);
  }
  if (fm.howToApply?.length)
    blocks.push(`<p><strong>How to apply</strong></p><ol>${fm.howToApply.map((s) => `<li>${esc(s)}</li>`).join("")}</ol>`);
  blocks.push(`<p>Verify all details in the official ${esc(org || "recruitment")} notification before applying.</p>`);
  return blocks.join("");
}

/** Parse "₹18,000 – ₹45,000 per month" → { min: 18000, max: 45000 } or null */
function parseSalaryRange(raw: string | undefined): { min: number; max: number } | null {
  if (!raw) return null;
  const nums = raw.replace(/[₹,\s]/g, "").match(/\d+/g);
  if (!nums || nums.length < 1) return null;
  const values = nums.map(Number).filter((n) => n >= 1000 && n <= 10_000_000);
  if (values.length === 0) return null;
  return { min: values[0], max: values[values.length - 1] };
}

/** Map a qualification string to a valid schema.org/Google JobPosting credentialCategory enum value */
function credentialCategory(qual: string | undefined): string | null {
  if (!qual) return null;
  const q = qual.toLowerCase();
  if (q.includes("post graduate") || q.includes("postgraduate") || q.includes("m.sc") || q.includes("m.a") ||
      q.includes("m.tech") || q.includes("mba") || q.includes("master")) return "postgraduate degree";
  if (q.includes("degree") || q.includes("graduate") || q.includes("b.sc") ||
      q.includes("b.a") || q.includes("b.com") || q.includes("b.e") || q.includes("b.tech") || q.includes("bachelor")) return "bachelor degree";
  if (q.includes("diploma")) return "associate degree";
  if (q.includes("10th") || q.includes("matriculation") || q.includes("sslc") || q.includes("class 10")) return "high school";
  if (q.includes("12th") || q.includes("intermediate") || q.includes("hsc") || q.includes("class 12")) return "high school";
  return null;
}

const REGIONS: Array<[RegExp, string, string]> = [
  [/madhya pradesh|mppsc|mpesb|\bmp\b/i, "Madhya Pradesh", "Bhopal"],
  [/uttar pradesh|uppsc|upsssc|\bup\b/i, "Uttar Pradesh", "Lucknow"],
  [/rajasthan|rpsc|rsmssb|rssb/i, "Rajasthan", "Jaipur"],
  [/bihar|bpsc|bssc|btsc|csbc|bpssc/i, "Bihar", "Patna"],
  [/gujarat|gpsc/i, "Gujarat", "Gandhinagar"],
  [/maharashtra|mpsc/i, "Maharashtra", "Mumbai"],
  [/karnataka|kpsc/i, "Karnataka", "Bengaluru"],
  [/tamil nadu|tnpsc/i, "Tamil Nadu", "Chennai"],
  [/andhra pradesh|appsc/i, "Andhra Pradesh", "Amaravati"],
  [/telangana|tspsc/i, "Telangana", "Hyderabad"],
  [/kerala/i, "Kerala", "Thiruvananthapuram"],
  [/west bengal|wbpsc|wbssc/i, "West Bengal", "Kolkata"],
  [/punjab|ppsc/i, "Punjab", "Chandigarh"],
  [/haryana|hpsc|hssc/i, "Haryana", "Chandigarh"],
  [/himachal|hppsc/i, "Himachal Pradesh", "Shimla"],
  [/jharkhand|jpsc|jssc/i, "Jharkhand", "Ranchi"],
  [/odisha|opsc|ossc/i, "Odisha", "Bhubaneswar"],
  [/chhattisgarh|cgpsc|cgvyapam/i, "Chhattisgarh", "Raipur"],
  [/assam|apsc/i, "Assam", "Guwahati"],
  [/uttarakhand|ukpsc|uksssc/i, "Uttarakhand", "Dehradun"],
];

function inferPlace(text: string): { region: string; locality: string } {
  for (const [rx, region, locality] of REGIONS) {
    if (rx.test(text)) return { region, locality };
  }
  return { region: "Delhi", locality: "New Delhi" };
}

const MAJOR_ORG_URLS: Record<string, string> = {
  "Staff Selection Commission": "https://ssc.gov.in",
  "Railway Recruitment Board": "https://www.rrbapply.gov.in",
  "Union Public Service Commission": "https://upsc.gov.in",
  "Institute of Banking Personnel Selection": "https://www.ibps.in",
  "State Bank of India": "https://www.sbi.co.in",
  "Reserve Bank of India": "https://www.rbi.org.in",
};

function orgUrl(fm: PostFrontmatter): string | undefined {
  if (fm.officialWebsite && /^https?:\/\//.test(fm.officialWebsite)) return fm.officialWebsite;
  const key = Object.keys(MAJOR_ORG_URLS).find((k) => (fm.organization || "").includes(k));
  return key ? MAJOR_ORG_URLS[key] : undefined;
}

export function buildJobJsonLd(fm: PostFrontmatter, url: string): object {
  const org = orgName(fm) || "Government of India";
  const datePosted = toIsoDate(fm.publishedAt) || toIsoDate(fm.updatedAt);
  const place = inferPlace(`${fm.organization || ""} ${fm.dept || ""} ${fm.title}`);
  const sameAs = orgUrl(fm);

  const ld: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "JobPosting",
    title: fm.title,
    description: buildJobDescriptionHtml(fm),
    url,
    ...(datePosted ? { datePosted } : {}),
    ...(fm.updatedAt && toIsoDate(fm.updatedAt) ? { dateModified: toIsoDate(fm.updatedAt) } : {}),
    employmentType: "FULL_TIME",
    industry: "Government",
    occupationalCategory: "Government Services",
    hiringOrganization: {
      "@type": "Organization",
      name: org,
      ...(sameAs ? { sameAs } : {}),
    },
    jobLocation: {
      "@type": "Place",
      address: {
        "@type": "PostalAddress",
        addressLocality: place.locality,
        addressRegion: place.region,
        addressCountry: "IN",
      },
    },
    applicantLocationRequirements: { "@type": "Country", name: "India" },
    directApply: false,
  };

  const validThrough = toIsoDate(fm.lastDate);
  if (validThrough) ld.validThrough = `${validThrough}T23:59:59+05:30`;

  const totalPosts = parseInt((fm.totalPosts || "").replace(/[^0-9]/g, ""), 10);
  if (totalPosts > 0) ld.totalJobOpenings = totalPosts;

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

  if (fm.qualification) {
    const category = credentialCategory(fm.qualification);
    ld.educationRequirements = {
      "@type": "EducationalOccupationalCredential",
      ...(category ? { credentialCategory: category } : {}),
      competencyRequired: fm.qualification,
    };
  }

  if (fm.advertisementNo) {
    ld.identifier = { "@type": "PropertyValue", name: "Advertisement Number", value: fm.advertisementNo };
  }

  return ld;
}

export function buildBreadcrumbJsonLd(crumbs: Array<{ label: string; href?: string }>): object {
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

const PUBLISHER = {
  "@type": "Organization",
  name: siteConfig.name,
  url: siteConfig.url,
  logo: { "@type": "ImageObject", url: `${siteConfig.url}/icon-512.png`, width: 512, height: 512 },
};

export function buildOrganizationJsonLd(): object {
  return {
    "@context": "https://schema.org",
    ...PUBLISHER,
    description: siteConfig.description,
    sameAs: [siteConfig.links.twitter, siteConfig.links.telegram],
  };
}

function buildArticleJsonLd(fm: PostFrontmatter, url: string): object {
  const org = orgName(fm) || "Government of India";
  const datePublished = toIsoDate(fm.publishedAt) || toIsoDate(fm.updatedAt);
  const dateModified = toIsoDate(fm.updatedAt) || datePublished;
  return {
    "@context": "https://schema.org",
    "@type": "NewsArticle",
    headline: fm.title.length > 110 ? fm.title.slice(0, 107) + "..." : fm.title,
    description: plainDescription(fm),
    url,
    mainEntityOfPage: { "@type": "WebPage", "@id": url },
    ...(datePublished ? { datePublished } : {}),
    ...(dateModified ? { dateModified } : {}),
    author: { "@type": "Organization", name: siteConfig.name, url: siteConfig.url },
    publisher: PUBLISHER,
    image: [`${siteConfig.url}${siteConfig.ogImage}`],
    inLanguage: "en-IN",
    about: { "@type": "Organization", name: org },
    isAccessibleForFree: true,
  };
}

export function buildResultJsonLd(fm: PostFrontmatter, url: string): object {
  return buildArticleJsonLd(fm, url);
}

export function buildAdmitJsonLd(fm: PostFrontmatter, url: string): object {
  return buildArticleJsonLd(fm, url);
}

export function buildAnswerKeyJsonLd(fm: PostFrontmatter, url: string): object {
  const org = orgName(fm) || "Government of India";
  const datePublished = toIsoDate(fm.publishedAt);
  return {
    "@context": "https://schema.org",
    "@type": "LearningResource",
    name: fm.title,
    description: plainDescription(fm),
    url,
    ...(datePublished ? { datePublished } : {}),
    provider: { "@type": "Organization", name: org },
    educationalUse: "Answer Key",
    inLanguage: "en-IN",
    isAccessibleForFree: true,
  };
}

export function buildSyllabusJsonLd(fm: PostFrontmatter, url: string): object {
  const org = orgName(fm) || "Government of India";
  const datePublished = toIsoDate(fm.publishedAt);
  return {
    "@context": "https://schema.org",
    "@type": "LearningResource",
    name: fm.title,
    description: plainDescription(fm),
    url,
    ...(datePublished ? { datePublished } : {}),
    provider: { "@type": "Organization", name: org },
    educationalUse: "Syllabus",
    learningResourceType: "Exam syllabus",
    inLanguage: "en-IN",
    isAccessibleForFree: true,
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
