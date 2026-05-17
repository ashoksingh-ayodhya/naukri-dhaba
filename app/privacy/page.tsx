import type { Metadata } from "next";
import { buildMetadata } from "@/lib/seo";
import Breadcrumb from "@/components/ui/Breadcrumb";

export const metadata: Metadata = buildMetadata({
  title: "Privacy Policy — Naukri Dhaba",
  description: "Naukri Dhaba privacy policy. Learn how we collect, use and protect your information when you use our government job portal.",
  path: "/privacy/",
});

export default function PrivacyPage() {
  const year = new Date().getFullYear();
  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <Breadcrumb crumbs={[{ label: "Home", href: "/" }, { label: "Privacy Policy" }]} />
      <div className="mt-6 card p-6 prose prose-sm max-w-none prose-headings:font-heading">
        <h1>Privacy Policy</h1>
        <p className="text-slate-500 text-xs">Last updated: January 1, {year}</p>

        <h2>Information We Collect</h2>
        <p>
          Naukri Dhaba does not require registration or login. We may collect anonymous usage data
          (pages visited, time spent) through analytics tools to improve the site. We do not collect
          personally identifiable information unless you contact us voluntarily.
        </p>

        <h2>Cookies</h2>
        <p>
          We use cookies for analytics purposes (Google Analytics) and to remember your preferences.
          You can disable cookies in your browser settings; however, some features of the site may
          not function correctly.
        </p>

        <h2>Third-Party Links</h2>
        <p>
          Our site contains links to official government websites and other third-party sites. We are
          not responsible for the privacy practices of those sites. We encourage you to read their
          privacy policies before providing any personal information.
        </p>

        <h2>Google Analytics</h2>
        <p>
          We use Google Analytics to understand how visitors use our site. Google Analytics collects
          anonymous data such as pages visited, browser type and location. This data is used solely
          to improve our service and is governed by{" "}
          <a href="https://policies.google.com/privacy" target="_blank" rel="noopener noreferrer">
            Google&apos;s Privacy Policy
          </a>.
        </p>

        <h2>Advertising</h2>
        <p>
          We may display advertisements served by Google AdSense or similar networks. These networks
          may use cookies to serve ads based on your prior visits to our site or other sites. You can
          opt out of personalized advertising by visiting{" "}
          <a href="https://www.google.com/settings/ads" target="_blank" rel="noopener noreferrer">
            Google Ads Settings
          </a>.
        </p>

        <h2>Data Security</h2>
        <p>
          We take reasonable precautions to protect the data we collect. However, no method of
          transmission over the Internet is 100% secure, and we cannot guarantee absolute security.
        </p>

        <h2>Changes to This Policy</h2>
        <p>
          We may update this Privacy Policy from time to time. Changes will be posted on this page
          with an updated date. Continued use of the site after changes constitutes acceptance of the
          revised policy.
        </p>

        <h2>Contact</h2>
        <p>
          If you have questions about this Privacy Policy, please <a href="/contact/">contact us</a>.
        </p>
      </div>
    </div>
  );
}
