export const dynamicParams = false;

import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getPostsByQualification, QualificationLevel } from "@/lib/content";
import { buildMetadata } from "@/lib/seo";
import PaginatedJobsTable from "@/components/listings/PaginatedJobsTable";
import Breadcrumb from "@/components/ui/Breadcrumb";

const YEAR = new Date().getFullYear();

const QUAL_META: Record<QualificationLevel, { title: string; h1: string; h2: string; description: string }> = {
  "10th-pass": {
    title: `10th Pass Govt Jobs ${YEAR} — Sarkari Naukri for Matric Pass`,
    h1: `10th Pass Govt Jobs ${YEAR}`,
    h2: `Latest Government Jobs for 10th Pass / Matric Candidates ${YEAR}`,
    description: `Find all ${YEAR} government job notifications open to 10th pass (Matriculation/SSLC) candidates. Apply for SSC, Railway, Police, Defence and other sarkari naukri requiring Class 10 qualification.`,
  },
  "12th-pass": {
    title: `12th Pass Govt Jobs ${YEAR} — Sarkari Naukri for Intermediate Pass`,
    h1: `12th Pass Govt Jobs ${YEAR}`,
    h2: `Latest Government Jobs for 12th Pass / Intermediate Candidates ${YEAR}`,
    description: `Browse ${YEAR} government job vacancies for 12th pass (HSC/Intermediate) candidates. Railway, SSC CHSL, Banking assistants, Police constable and more sarkari naukri for Class 12 pass.`,
  },
  diploma: {
    title: `Diploma / ITI Govt Jobs ${YEAR} — Latest Sarkari Naukri`,
    h1: `Diploma & ITI Govt Jobs ${YEAR}`,
    h2: `Latest Government Jobs for Diploma / ITI Certificate Holders ${YEAR}`,
    description: `All ${YEAR} government job vacancies for Diploma and ITI certificate holders. Apply for Junior Engineer, Technician, Trade Apprentice and other technical sarkari naukri.`,
  },
  graduate: {
    title: `Graduate Govt Jobs ${YEAR} — Any Degree Sarkari Naukri`,
    h1: `Graduate Govt Jobs ${YEAR}`,
    h2: `Latest Government Jobs for Graduate / Any Degree Candidates ${YEAR}`,
    description: `${YEAR} government job notifications open to graduates (any stream — BA, B.Sc, B.Com, BCA). SSC CGL, UPSC, Banking, PSU and state government jobs for degree holders.`,
  },
  engineering: {
    title: `Engineering Govt Jobs ${YEAR} — BE / B.Tech Sarkari Naukri`,
    h1: `Engineering Govt Jobs ${YEAR}`,
    h2: `Latest Government Jobs for BE / B.Tech / Engineering Graduates ${YEAR}`,
    description: `Latest ${YEAR} government jobs for engineering graduates (BE/B.Tech). PSU jobs in DRDO, ISRO, NTPC, ONGC, BEL, BHEL; Junior Engineer posts in SSC JE, RRB JE and state PWD.`,
  },
  postgraduate: {
    title: `Post Graduate Govt Jobs ${YEAR} — M.Sc / MBA / M.Tech Sarkari Naukri`,
    h1: `Post Graduate Govt Jobs ${YEAR}`,
    h2: `Latest Government Jobs for Post Graduates (M.Sc / MBA / M.Tech / PhD) ${YEAR}`,
    description: `${YEAR} government job vacancies requiring post graduation (Master's degree, MBA, M.Tech, PhD). Research fellowships, PSU officer roles, UPSC Group A and other sarkari naukri for post graduates.`,
  },
};

interface Props {
  params: Promise<{ level: string }>;
}

export function generateStaticParams() {
  const levels: QualificationLevel[] = ["10th-pass", "12th-pass", "diploma", "graduate", "engineering", "postgraduate"];
  return levels.map((level) => ({ level }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { level } = await params;
  const meta = QUAL_META[level as QualificationLevel];
  if (!meta) return {};
  return buildMetadata({
    title: meta.title,
    description: meta.description,
    path: `/jobs/qualification/${level}/`,
  });
}

export default async function QualificationPage({ params }: Props) {
  const { level } = await params;
  const meta = QUAL_META[level as QualificationLevel];
  if (!meta) notFound();

  const posts = getPostsByQualification(level as QualificationLevel);

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <Breadcrumb
        crumbs={[
          { label: "Home", href: "/" },
          { label: "Jobs", href: "/jobs/" },
          { label: meta.h1 },
        ]}
      />
      <div className="mt-4 mb-6">
        <h1 className="font-heading text-2xl md:text-3xl font-bold text-slate-900 mb-1">{meta.h1}</h1>
        <h2 className="text-base font-semibold text-slate-700 mt-1 mb-1">{meta.h2}</h2>
        <p className="text-slate-500 text-sm">{posts.length} vacancies found</p>
      </div>
      <p className="text-slate-600 text-sm leading-relaxed mb-6">{meta.description}</p>
      <PaginatedJobsTable posts={posts} title={meta.h1} showHeader={false} />
    </div>
  );
}
