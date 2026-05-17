import type { Metadata } from "next";
import { buildMetadata } from "@/lib/seo";
import { siteConfig } from "@/config/site";
import Breadcrumb from "@/components/ui/Breadcrumb";

export const metadata: Metadata = buildMetadata({
  title: "Contact Us — Naukri Dhaba",
  description: "Contact Naukri Dhaba for queries about government job notifications, corrections, partnership or advertising. Reach us on Telegram or WhatsApp.",
  path: "/contact/",
});

export default function ContactPage() {
  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <Breadcrumb crumbs={[{ label: "Home", href: "/" }, { label: "Contact Us" }]} />
      <div className="mt-6 space-y-4">
        <div className="card p-6">
          <h1 className="font-heading text-2xl font-bold text-slate-900 mb-2">Contact Us</h1>
          <p className="text-slate-600 text-sm leading-relaxed">
            Have a question about a job notification, spotted an error, or want to collaborate?
            Reach out to us through any of the channels below. We typically respond within 24 hours.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <a
            href={siteConfig.links.telegram}
            target="_blank"
            rel="noopener noreferrer"
            className="card p-5 hover:shadow-md transition-shadow group"
          >
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center shrink-0 text-xl">
                ✈️
              </div>
              <div>
                <h2 className="font-semibold text-slate-900 group-hover:text-primary-700 transition-colors">Telegram</h2>
                <p className="text-sm text-slate-500 mt-1">Join our Telegram channel for daily job updates and to reach us directly.</p>
              </div>
            </div>
          </a>

          <a
            href={siteConfig.links.whatsapp}
            target="_blank"
            rel="noopener noreferrer"
            className="card p-5 hover:shadow-md transition-shadow group"
          >
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center shrink-0 text-xl">
                💬
              </div>
              <div>
                <h2 className="font-semibold text-slate-900 group-hover:text-primary-700 transition-colors">WhatsApp</h2>
                <p className="text-sm text-slate-500 mt-1">Join our WhatsApp group for instant notifications and support queries.</p>
              </div>
            </div>
          </a>
        </div>

        <div className="card p-6">
          <h2 className="font-heading font-semibold text-slate-900 mb-3">Common Queries</h2>
          <ul className="space-y-3 text-sm text-slate-600">
            <li className="flex gap-2">
              <span className="text-green-500 shrink-0 font-bold">→</span>
              <span><strong>Corrections:</strong> If you spot incorrect information (wrong date, fee, or link), message us on Telegram with the page URL and the correct detail.</span>
            </li>
            <li className="flex gap-2">
              <span className="text-green-500 shrink-0 font-bold">→</span>
              <span><strong>Missing notifications:</strong> We cover all major central and state recruitments. If we missed one, send us the official notification link on Telegram.</span>
            </li>
            <li className="flex gap-2">
              <span className="text-green-500 shrink-0 font-bold">→</span>
              <span><strong>Advertising:</strong> For advertising or sponsored content enquiries, reach out via Telegram.</span>
            </li>
            <li className="flex gap-2">
              <span className="text-green-500 shrink-0 font-bold">→</span>
              <span><strong>Copyright:</strong> For copyright concerns, contact us via Telegram with full details and we will respond within 48 hours.</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
