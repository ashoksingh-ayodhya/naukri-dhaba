export const siteConfig = {
  name: "Naukri Dhaba",
  tagline: "India's Trusted Sarkari Naukri Portal",
  description:
    "Get latest government job notifications, exam results, admit cards, answer keys and syllabus. Naukri Dhaba covers SSC, Railway, Banking, UPSC, Police, Defence and all state govt jobs.",
  url: process.env.NEXT_PUBLIC_SITE_URL || "https://naukridhaba.in",
  ogImage: "/og-default.png",
  links: {
    twitter: "https://twitter.com/naukridhaba",
    telegram: "https://t.me/naukridhaba",
    whatsapp: "https://whatsapp.com/channel/naukridhaba",
  },
} as const;

export const CATEGORIES = [
  { slug: "ssc", label: "SSC", fullName: "Staff Selection Commission", icon: "🏛️" },
  { slug: "railway", label: "Railway", fullName: "Railway Recruitment Boards", icon: "🚂" },
  { slug: "banking", label: "Banking", fullName: "Banking & Insurance", icon: "🏦" },
  { slug: "upsc", label: "UPSC", fullName: "Union Public Service Commission", icon: "📋" },
  { slug: "police", label: "Police", fullName: "Police & Paramilitary", icon: "👮" },
  { slug: "defence", label: "Defence", fullName: "Army, Navy & Air Force", icon: "🎖️" },
  { slug: "teaching", label: "Teaching", fullName: "Teaching & Education", icon: "📚" },
  { slug: "psu", label: "PSU", fullName: "Public Sector Undertakings", icon: "🏭" },
  { slug: "state-psc", label: "State PSC", fullName: "State Public Service Commissions", icon: "🏛️" },
  { slug: "postal", label: "Postal", fullName: "India Post & Postal Services", icon: "✉️" },
  { slug: "medical", label: "Medical", fullName: "Medical & Health Dept", icon: "🏥" },
  { slug: "government", label: "Govt", fullName: "Other Government Jobs", icon: "🇮🇳" },
] as const;

export type CategorySlug = (typeof CATEGORIES)[number]["slug"];

export const CONTENT_TYPES = [
  { slug: "jobs", label: "Latest Jobs", shortLabel: "Jobs", navLabel: "Jobs" },
  { slug: "results", label: "Results", shortLabel: "Results", navLabel: "Results" },
  { slug: "admit-cards", label: "Admit Cards", shortLabel: "Admit Cards", navLabel: "Admit Cards" },
  { slug: "answer-keys", label: "Answer Keys", shortLabel: "Answer Keys", navLabel: "Answer Keys" },
  { slug: "syllabus", label: "Syllabus", shortLabel: "Syllabus", navLabel: "Syllabus" },
] as const;

export const STATES = [
  { slug: "uttar-pradesh", label: "Uttar Pradesh", abbr: "UP" },
  { slug: "bihar", label: "Bihar", abbr: "BR" },
  { slug: "rajasthan", label: "Rajasthan", abbr: "RJ" },
  { slug: "madhya-pradesh", label: "Madhya Pradesh", abbr: "MP" },
  { slug: "haryana", label: "Haryana", abbr: "HR" },
  { slug: "jharkhand", label: "Jharkhand", abbr: "JH" },
  { slug: "delhi", label: "Delhi", abbr: "DL" },
  { slug: "maharashtra", label: "Maharashtra", abbr: "MH" },
  { slug: "gujarat", label: "Gujarat", abbr: "GJ" },
  { slug: "punjab", label: "Punjab", abbr: "PB" },
  { slug: "karnataka", label: "Karnataka", abbr: "KA" },
  { slug: "tamil-nadu", label: "Tamil Nadu", abbr: "TN" },
  { slug: "andhra-pradesh", label: "Andhra Pradesh", abbr: "AP" },
  { slug: "telangana", label: "Telangana", abbr: "TS" },
  { slug: "west-bengal", label: "West Bengal", abbr: "WB" },
  { slug: "odisha", label: "Odisha", abbr: "OD" },
  { slug: "chhattisgarh", label: "Chhattisgarh", abbr: "CG" },
  { slug: "uttarakhand", label: "Uttarakhand", abbr: "UK" },
  { slug: "himachal-pradesh", label: "Himachal Pradesh", abbr: "HP" },
  { slug: "assam", label: "Assam", abbr: "AS" },
] as const;

export type StateSlug = (typeof STATES)[number]["slug"];

export const MIN_POST_DATE = "2022-01-01";
