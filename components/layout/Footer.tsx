import Link from "next/link";
import { CATEGORIES, STATES, siteConfig } from "@/config/site";

export default function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="bg-slate-900 text-slate-300 mt-12">
      {/* Main footer grid */}
      <div className="max-w-7xl mx-auto px-4 py-10 grid grid-cols-2 md:grid-cols-4 gap-8">
        {/* Brand */}
        <div className="col-span-2 md:col-span-1">
          <Link href="/" className="flex items-center gap-2 font-heading font-bold text-lg text-white mb-3">
            <span className="text-accent-500">🍽️</span>
            <span>Naukri Dhaba</span>
          </Link>
          <p className="text-sm text-slate-400 leading-relaxed mb-4">
            India&apos;s trusted portal for government job notifications, results, admit cards and exam updates. Updated daily.
          </p>
          <div className="flex gap-3">
            <a href={siteConfig.links.telegram} target="_blank" rel="noopener noreferrer" className="text-slate-400 hover:text-white transition-colors text-sm">
              Telegram
            </a>
            <a href={siteConfig.links.whatsapp} target="_blank" rel="noopener noreferrer" className="text-slate-400 hover:text-white transition-colors text-sm">
              WhatsApp
            </a>
          </div>
        </div>

        {/* Quick links */}
        <div>
          <h3 className="text-white font-semibold text-sm uppercase tracking-wide mb-3">Quick Links</h3>
          <ul className="space-y-2">
            {[
              { href: "/latest-jobs/", label: "Latest Jobs" },
              { href: "/results/", label: "Results" },
              { href: "/admit-cards/", label: "Admit Cards" },
              { href: "/answer-keys/", label: "Answer Keys" },
              { href: "/syllabus/", label: "Syllabus" },
              { href: "/search/", label: "Search" },
            ].map((link) => (
              <li key={link.href}>
                <Link href={link.href} className="text-sm text-slate-400 hover:text-white transition-colors">
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>

        {/* Job Categories */}
        <div>
          <h3 className="text-white font-semibold text-sm uppercase tracking-wide mb-3">Categories</h3>
          <ul className="space-y-2">
            {CATEGORIES.slice(0, 8).map((cat) => (
              <li key={cat.slug}>
                <Link href={`/jobs/${cat.slug}/`} className="text-sm text-slate-400 hover:text-white transition-colors">
                  {cat.fullName}
                </Link>
              </li>
            ))}
          </ul>
        </div>

        {/* State Jobs */}
        <div>
          <h3 className="text-white font-semibold text-sm uppercase tracking-wide mb-3">State Jobs</h3>
          <ul className="space-y-2">
            {STATES.slice(0, 10).map((state) => (
              <li key={state.slug}>
                <Link href={`/state/${state.slug}/`} className="text-sm text-slate-400 hover:text-white transition-colors">
                  {state.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Bottom bar */}
      <div className="border-t border-slate-800">
        <div className="max-w-7xl mx-auto px-4 py-4 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-slate-500">
          <p>© {year} Naukri Dhaba. All rights reserved.</p>
          <div className="flex gap-4">
            <Link href="/about/" className="hover:text-slate-300 transition-colors">About</Link>
            <Link href="/privacy/" className="hover:text-slate-300 transition-colors">Privacy Policy</Link>
            <Link href="/disclaimer/" className="hover:text-slate-300 transition-colors">Disclaimer</Link>
            <Link href="/contact/" className="hover:text-slate-300 transition-colors">Contact</Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
