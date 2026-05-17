import type { Metadata } from "next";
import { buildMetadata } from "@/lib/seo";
import Breadcrumb from "@/components/ui/Breadcrumb";

export const metadata: Metadata = buildMetadata({
  title: "About Naukri Dhaba — India's Government Job Portal",
  description: "Naukri Dhaba is India's trusted portal for government job notifications, exam results, admit cards, answer keys and syllabus. Updated daily from official sources.",
  path: "/about/",
});

export default function AboutPage() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <Breadcrumb crumbs={[{ label: "Home", href: "/" }, { label: "About Us" }]} />
      <div className="mt-6 card p-6 prose prose-sm max-w-none prose-headings:font-heading">
        <h1>About Naukri Dhaba</h1>
        <p>
          Naukri Dhaba is India&apos;s trusted portal for government job seekers. We aggregate and publish
          the latest recruitment notifications, exam results, admit cards, answer keys and syllabus from
          all major government bodies — SSC, Railway, UPSC, Banking, Police, Defence, and more.
        </p>
        <h2>What We Do</h2>
        <ul>
          <li>Publish daily government job notifications from official sources</li>
          <li>Provide direct links to official websites for apply, notification and results</li>
          <li>Cover all major recruitment bodies: SSC, RRB, IBPS, UPSC, State PSCs and more</li>
          <li>Share exam results, admit cards, answer keys and syllabi as soon as they are released</li>
        </ul>
        <h2>Our Mission</h2>
        <p>
          Our mission is to make government job information accessible to every aspirant in India,
          especially those from rural areas with limited internet access, by presenting official
          notifications in a clear, mobile-friendly format.
        </p>
        <h2>Disclaimer</h2>
        <p>
          All information on Naukri Dhaba is sourced from official government websites and notifications.
          We are not affiliated with any government organization. Candidates are advised to verify all
          details from the official website before applying.
        </p>
        <h2>Contact</h2>
        <p>
          For queries, corrections or partnership enquiries, please visit our{" "}
          <a href="/contact/">Contact page</a>.
        </p>
      </div>
    </div>
  );
}
