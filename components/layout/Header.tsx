"use client";

import Link from "next/link";
import { useState } from "react";
import { CONTENT_TYPES, CATEGORIES, siteConfig } from "@/config/site";

const NAV_LINKS = [
  { href: "/latest-jobs/", label: "Latest Jobs" },
  { href: "/results/", label: "Results" },
  { href: "/admit-cards/", label: "Admit Cards" },
  { href: "/answer-keys/", label: "Answer Keys" },
  { href: "/syllabus/", label: "Syllabus" },
];

export default function Header() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [jobsDropdown, setJobsDropdown] = useState(false);

  return (
    <header className="sticky top-0 z-50 bg-primary-900 text-white shadow-lg">
      {/* Top bar */}
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between h-14">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 font-heading font-bold text-xl tracking-tight">
            <span className="text-accent-500">🍽️</span>
            <span className="text-white">Naukri</span>
            <span className="text-accent-400">Dhaba</span>
          </Link>

          {/* Desktop nav */}
          <nav className="hidden md:flex items-center gap-1">
            {/* Jobs with dropdown */}
            <div
              className="relative"
              onMouseEnter={() => setJobsDropdown(true)}
              onMouseLeave={() => setJobsDropdown(false)}
            >
              <Link
                href="/latest-jobs/"
                className="px-3 py-2 rounded-md text-sm font-medium text-white/90 hover:text-white hover:bg-white/10 transition-colors flex items-center gap-1"
              >
                Jobs
                <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
              </Link>
              {jobsDropdown && (
                <div className="absolute top-full left-0 bg-white text-slate-800 rounded-lg shadow-xl border border-slate-100 py-2 w-48 grid grid-cols-2 gap-0">
                  {CATEGORIES.map((cat) => (
                    <Link
                      key={cat.slug}
                      href={`/jobs/${cat.slug}/`}
                      className="px-3 py-1.5 text-sm hover:bg-slate-50 hover:text-primary-900 transition-colors"
                    >
                      {cat.label}
                    </Link>
                  ))}
                </div>
              )}
            </div>

            {NAV_LINKS.slice(1).map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="px-3 py-2 rounded-md text-sm font-medium text-white/90 hover:text-white hover:bg-white/10 transition-colors"
              >
                {link.label}
              </Link>
            ))}
          </nav>

          {/* Search + mobile toggle */}
          <div className="flex items-center gap-2">
            <Link
              href="/search/"
              className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-white/10 hover:bg-white/20 rounded-lg text-sm text-white/80 hover:text-white transition-colors"
              aria-label="Search"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <span>Search</span>
            </Link>

            <button
              className="md:hidden p-2 rounded-md hover:bg-white/10 transition-colors"
              onClick={() => setMobileOpen(!mobileOpen)}
              aria-label="Toggle menu"
            >
              {mobileOpen ? (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Category strip */}
      <div className="hidden md:block bg-primary-950 border-t border-white/10">
        <div className="max-w-7xl mx-auto px-4 flex items-center gap-0 overflow-x-auto scrollbar-none h-9">
          {CATEGORIES.map((cat) => (
            <Link
              key={cat.slug}
              href={`/jobs/${cat.slug}/`}
              className="whitespace-nowrap px-3 h-full flex items-center text-xs font-medium text-white/70 hover:text-white hover:bg-white/10 transition-colors border-r border-white/10 last:border-0"
            >
              {cat.label}
            </Link>
          ))}
        </div>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="md:hidden bg-primary-950 border-t border-white/10">
          <div className="px-4 py-3 space-y-1">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileOpen(false)}
                className="block px-3 py-2 rounded-md text-sm font-medium text-white/90 hover:text-white hover:bg-white/10 transition-colors"
              >
                {link.label}
              </Link>
            ))}
            <div className="pt-2 border-t border-white/10">
              <p className="px-3 pb-1 text-xs text-white/50 uppercase tracking-wide font-semibold">Categories</p>
              <div className="grid grid-cols-3 gap-1">
                {CATEGORIES.map((cat) => (
                  <Link
                    key={cat.slug}
                    href={`/jobs/${cat.slug}/`}
                    onClick={() => setMobileOpen(false)}
                    className="px-2 py-1.5 rounded text-xs text-white/80 hover:text-white hover:bg-white/10 transition-colors"
                  >
                    {cat.label}
                  </Link>
                ))}
              </div>
            </div>
            <Link
              href="/search/"
              onClick={() => setMobileOpen(false)}
              className="flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium text-white/90 hover:text-white hover:bg-white/10 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              Search
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}
