export type PageType = "job" | "result" | "admit" | "answer-key" | "syllabus";

export interface VacancyRow {
  post_name: string;
  general?: string;
  ews?: string;
  obc?: string;
  sc?: string;
  st?: string;
  total?: string;
  eligibility?: string;
}

export interface ImportantLink {
  label: string;
  url: string;
  link_type:
    | "apply"
    | "result"
    | "admit"
    | "notification"
    | "answer_key"
    | "syllabus"
    | "exam_city"
    | "eligibility"
    | "official_website"
    | "other";
}

export interface PostFrontmatter {
  title: string;
  slug: string;
  type: PageType;
  category: string;
  dept: string;
  organization: string;
  advertisementNo?: string;
  totalPosts?: string;
  lastDate?: string;
  applicationBegin?: string;
  examDate?: string;
  admitDate?: string;
  resultDate?: string;
  ageMin?: number;
  ageMax?: number;
  ageReferenceDate?: string;
  ageRelaxationNotes?: string;
  qualification?: string;
  qualificationItems?: string[];
  feeGeneral?: string;
  feeSCST?: string;
  feePaymentMethod?: string;
  salary?: string;
  applyUrl?: string;
  notificationUrl?: string;
  resultUrl?: string;
  admitUrl?: string;
  officialWebsite?: string;
  publishedAt: string;
  updatedAt?: string;
  source?: string;
  sourceUrl?: string;
  shortDescription?: string;
  dates?: Record<string, string>;
  fees?: Record<string, string>;
  vacancyBreakdown?: VacancyRow[];
  importantLinks?: ImportantLink[];
  howToApply?: string[];
}

export interface PostMeta extends PostFrontmatter {
  contentPath: string;
}

export interface ListingPost {
  title: string;
  slug: string;
  type: PageType;
  category: string;
  dept: string;
  organization: string;
  totalPosts?: string;
  lastDate?: string;
  publishedAt: string;
  updatedAt?: string;
  applyUrl?: string;
  href: string;
}
