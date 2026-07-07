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

const MONTH_NAMES: Record<string, string> = {
  jan: "01", feb: "02", mar: "03", apr: "04", may: "05", jun: "06",
  jul: "07", aug: "08", sep: "09", oct: "10", nov: "11", dec: "12",
};

function toIsoDate(raw: string | undefined): string | undefined {
  if (!raw) return undefined;
  if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw;
  // Accept both DD/MM/YYYY and DD-MM-YYYY separators — handles "13/02/2026 (Extended)" etc.
  const m = raw.match(/(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})/);
  if (m) return `${m[3]}-${m[2].padStart(2, "0")}-${m[1].padStart(2, "0")}`;
  // Accept textual month-name dates — "27 July 2026" (common on freejobalert).
  const t = raw.match(/(\d{1,2})\s+([A-Za-z]{3,})\s+(\d{4})/);
  if (t) {
    const month = MONTH_NAMES[t[2].slice(0, 3).toLowerCase()];
    if (month) return `${t[3]}-${month}-${t[1].padStart(2, "0")}`;
  }
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

type OrgAddress = {
  locality: string;
  region: string;
  postalCode?: string;
  streetAddress?: string;
};

/**
 * Exact-match central organizations (key == fm.organization, same keys as MAJOR_ORG_URLS).
 * Only orgs with a single, confidently verified HQ are included. Deliberately omitted:
 * Railway Recruitment Board (21 decentralized zonal boards, no single accurate HQ),
 * India Post (PIN conflicts across sources, 110001 vs 110116), and National Health Mission
 * (no dedicated building — operates inside the Ministry's Nirman Bhawan).
 */
const CENTRAL_ORG_ADDRESS: Record<string, OrgAddress> = {
  "Staff Selection Commission": { locality: "New Delhi", region: "Delhi", postalCode: "110003", streetAddress: "Block No. 12, CGO Complex, Lodhi Road" },
  "Union Public Service Commission": { locality: "New Delhi", region: "Delhi", postalCode: "110069", streetAddress: "Dholpur House, Shahjahan Road" },
  "Institute of Banking Personnel Selection": { locality: "Mumbai", region: "Maharashtra", postalCode: "400101", streetAddress: "IBPS House, 90 Feet D.P. Road, Off Western Express Highway, Kandivali (East)" },
  "State Bank of India": { locality: "Mumbai", region: "Maharashtra", postalCode: "400021", streetAddress: "State Bank Bhavan, Madame Cama Road, Nariman Point" },
  "Reserve Bank of India": { locality: "Mumbai", region: "Maharashtra", postalCode: "400001", streetAddress: "Central Office Building, Shahid Bhagat Singh Marg, Fort" },
  "National Bank for Agriculture and Rural Development": { locality: "Mumbai", region: "Maharashtra", postalCode: "400051", streetAddress: "Plot C-24, 'G' Block, Bandra Kurla Complex, Bandra (East)" },
  "Life Insurance Corporation": { locality: "Mumbai", region: "Maharashtra", postalCode: "400021", streetAddress: "Yogakshema, Jeevan Bima Marg, Nariman Point" },
  "DRDO": { locality: "New Delhi", region: "Delhi", postalCode: "110011", streetAddress: "DRDO Bhawan, Rajaji Marg" },
  "ISRO": { locality: "Bengaluru", region: "Karnataka", postalCode: "560094", streetAddress: "Antariksh Bhavan, New BEL Road" },
  "AIIMS": { locality: "New Delhi", region: "Delhi", postalCode: "110029", streetAddress: "Sri Aurobindo Marg, Ansari Nagar" },
  "NTPC": { locality: "New Delhi", region: "Delhi", postalCode: "110003", streetAddress: "NTPC Bhawan, SCOPE Complex, 7 Institutional Area, Lodhi Road" },
  "ONGC": { locality: "Dehradun", region: "Uttarakhand", postalCode: "248003", streetAddress: "Tel Bhavan" },
  "Indian Navy": { locality: "New Delhi", region: "Delhi", postalCode: "110011", streetAddress: "Integrated Headquarters, Ministry of Defence (Navy), Sena Bhawan" },
  "Indian Army": { locality: "New Delhi", region: "Delhi", postalCode: "110011", streetAddress: "Integrated Headquarters, Ministry of Defence (Army), South Block" },
  "Indian Air Force": { locality: "New Delhi", region: "Delhi", postalCode: "110011", streetAddress: "Integrated Headquarters, Ministry of Defence (Air Force), Vayu Bhawan" },
  "Indian Coast Guard": { locality: "New Delhi", region: "Delhi", postalCode: "110001", streetAddress: "Coast Guard Headquarters, National Stadium Complex" },
};

/**
 * Substring-matched state PSCs / selection boards, checked in order — more specific
 * acronyms first so e.g. RPSC (Ajmer) and RSMSSB (Jaipur), both Rajasthan, don't
 * collapse onto one address. APPSC is deliberately omitted: its HQ is reported to be
 * moving from Hyderabad to Vijayawada and the exact current street address is unconfirmed.
 */
const STATE_ORG_ADDRESS: Array<{ test: (o: string) => boolean; address: OrgAddress }> = [
  { test: (o) => o.includes("mppsc") || o.includes("madhya pradesh"), address: { locality: "Indore", region: "Madhya Pradesh", postalCode: "452001", streetAddress: "Residency Area, Daly College Road" } },
  { test: (o) => o.includes("upsssc"), address: { locality: "Lucknow", region: "Uttar Pradesh", postalCode: "226010", streetAddress: "3rd Floor, PICUP Bhawan, Vibhuti Khand, Gomti Nagar" } },
  { test: (o) => o.includes("uppsc") || o.includes("uttar pradesh"), address: { locality: "Prayagraj", region: "Uttar Pradesh", postalCode: "211001", streetAddress: "10, Kasturba Gandhi Marg, Civil Lines" } },
  { test: (o) => o.includes("rpsc"), address: { locality: "Ajmer", region: "Rajasthan", postalCode: "305001", streetAddress: "Ghooghra Ghati, Jaipur Road" } },
  { test: (o) => o.includes("rsmssb") || o.includes("rajasthan"), address: { locality: "Jaipur", region: "Rajasthan", postalCode: "302018", streetAddress: "SIAM Premises, Tonk Road, Durgapura" } },
  { test: (o) => o.includes("bssc"), address: { locality: "Patna", region: "Bihar", postalCode: "800014", streetAddress: "Near Veterinary College, Sheikhpura" } },
  { test: (o) => o.includes("bpsc") || o.includes("bihar"), address: { locality: "Patna", region: "Bihar", postalCode: "800001", streetAddress: "15, Nehru Path (Bailey Road)" } },
  { test: (o) => o.includes("gpsc") || o.includes("gujarat"), address: { locality: "Gandhinagar", region: "Gujarat", postalCode: "382010", streetAddress: "Sector 10-A, Near CHH-3 Circle" } },
  { test: (o) => o.includes("mpsc") || o.includes("maharashtra"), address: { locality: "Mumbai", region: "Maharashtra", postalCode: "400001", streetAddress: "3rd Floor, Bank of India Building, Opp. High Court, M.G. Road, Fort" } },
  { test: (o) => o.includes("kpsc") || o.includes("karnataka"), address: { locality: "Bengaluru", region: "Karnataka", postalCode: "560001", streetAddress: "Udyoga Soudha" } },
  { test: (o) => o.includes("tnpsc") || o.includes("tamil nadu"), address: { locality: "Chennai", region: "Tamil Nadu", postalCode: "600003", streetAddress: "TNPSC Road, V.O.C. Nagar, Park Town" } },
  { test: (o) => o.includes("appsc") || o.includes("andhra pradesh"), address: { locality: "Vijayawada", region: "Andhra Pradesh" } },
  { test: (o) => o.includes("tspsc") || o.includes("telangana"), address: { locality: "Hyderabad", region: "Telangana", postalCode: "500001", streetAddress: "Prathibha Bhavan, M.J. Road, Nampally" } },
  { test: (o) => o.includes("kerala"), address: { locality: "Thiruvananthapuram", region: "Kerala", postalCode: "695004", streetAddress: "Thulasi Hills, Pattom Palace P.O." } },
  { test: (o) => o.includes("wbpsc") || o.includes("wbssc") || o.includes("west bengal"), address: { locality: "Kolkata", region: "West Bengal", postalCode: "700026", streetAddress: "161-A, S.P. Mukherjee Road" } },
  { test: (o) => o.includes("ppsc") || o.includes("punjab"), address: { locality: "Patiala", region: "Punjab", postalCode: "147001", streetAddress: "Baradari Garden" } },
  { test: (o) => o.includes("hpsc") || o.includes("hssc") || o.includes("haryana"), address: { locality: "Panchkula", region: "Haryana", postalCode: "134112", streetAddress: "Bays 1-10, Block B, Sector 4" } },
  { test: (o) => o.includes("hppsc") || o.includes("himachal"), address: { locality: "Shimla", region: "Himachal Pradesh", postalCode: "171002", streetAddress: "Nigam Vihar" } },
  { test: (o) => o.includes("jpsc") || o.includes("jssc") || o.includes("jharkhand"), address: { locality: "Ranchi", region: "Jharkhand", postalCode: "834001", streetAddress: "Circular Road, Deputy Para, Ahirtoli" } },
  { test: (o) => o.includes("opsc") || o.includes("ossc") || o.includes("odisha"), address: { locality: "Cuttack", region: "Odisha", postalCode: "753001", streetAddress: "19, Dr. P.K. Parija Road, Buxi Bazar" } },
  { test: (o) => o.includes("cgpsc") || o.includes("cgvyapam") || o.includes("chhattisgarh"), address: { locality: "Raipur", region: "Chhattisgarh", postalCode: "492001", streetAddress: "Shankar Nagar Road, Bhagat Singh Square" } },
  { test: (o) => o.includes("apsc") || o.includes("slrc") || o.includes("assam"), address: { locality: "Guwahati", region: "Assam", postalCode: "781022", streetAddress: "Jawahar Nagar, Khanapara" } },
  { test: (o) => o.includes("uksssc"), address: { locality: "Dehradun", region: "Uttarakhand", postalCode: "248008", streetAddress: "Thano Road, near Maharana Pratap Sports College, Raipur" } },
  { test: (o) => o.includes("ukpsc") || o.includes("uttarakhand"), address: { locality: "Haridwar", region: "Uttarakhand", postalCode: "249404", streetAddress: "Singh Dwar, Kankhal" } },
];

/** Resolve the most accurate known address for a hiring org name — falls back to New Delhi. */
function resolveOrgAddress(rawOrgName: string): OrgAddress {
  const exact = CENTRAL_ORG_ADDRESS[rawOrgName.trim()];
  if (exact) return exact;
  const o = rawOrgName.toLowerCase();
  const matched = STATE_ORG_ADDRESS.find((rule) => rule.test(o));
  if (matched) return matched.address;
  return { locality: "New Delhi", region: "Delhi" };
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

  const orgAddress = resolveOrgAddress(orgName);

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
        addressLocality: orgAddress.locality,
        addressRegion: orgAddress.region,
        addressCountry: "IN",
        ...(orgAddress.postalCode ? { postalCode: orgAddress.postalCode } : {}),
        ...(orgAddress.streetAddress ? { streetAddress: orgAddress.streetAddress } : {}),
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
