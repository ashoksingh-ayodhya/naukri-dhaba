import type { Metadata } from "next";
import { buildMetadata } from "@/lib/seo";
import Breadcrumb from "@/components/ui/Breadcrumb";

export const metadata: Metadata = buildMetadata({
  title: "Disclaimer — Naukri Dhaba",
  description: "Naukri Dhaba disclaimer. All government job information is sourced from official websites. Candidates must verify details from official sources before applying.",
  path: "/disclaimer/",
});

export default function DisclaimerPage() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <Breadcrumb crumbs={[{ label: "Home", href: "/" }, { label: "Disclaimer" }]} />
      <div className="mt-6 card p-6 prose prose-sm max-w-none prose-headings:font-heading">
        <h1>Disclaimer</h1>

        <h2>Information Accuracy</h2>
        <p>
          Naukri Dhaba strives to provide accurate and up-to-date information about government job
          notifications, exam results, admit cards, answer keys and syllabi. However, we do not
          guarantee the accuracy, completeness or timeliness of any information published on this site.
        </p>
        <p>
          All recruitment information is sourced from official government websites and notifications.
          Candidates are strongly advised to verify all details — including eligibility, last date,
          application fee and instructions — directly from the official website before applying.
        </p>

        <h2>No Affiliation</h2>
        <p>
          Naukri Dhaba is an independent information portal and is not affiliated with, endorsed by,
          or officially connected to any government organization, ministry, department, board,
          commission or recruitment body mentioned on this site.
        </p>

        <h2>External Links</h2>
        <p>
          This site contains links to official government portals and third-party websites. These
          links are provided for convenience only. We do not control the content of external sites
          and are not responsible for any errors, omissions or changes made by those sites after we
          publish a link.
        </p>

        <h2>No Liability</h2>
        <p>
          Naukri Dhaba and its operators shall not be liable for any loss, damage or inconvenience
          arising from the use of information on this site. Candidates apply for any position
          entirely at their own risk.
        </p>

        <h2>Copyright</h2>
        <p>
          Content on Naukri Dhaba is either original editorial content or information summarized from
          official public domain sources. If you believe any content infringes your copyright, please
          contact us and we will address the matter promptly.
        </p>

        <h2>Updates</h2>
        <p>
          We reserve the right to modify this disclaimer at any time. Continued use of the site after
          changes implies acceptance of the updated disclaimer.
        </p>
      </div>
    </div>
  );
}
