"use client";

import { useState, useEffect, useMemo } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { Suspense } from "react";

interface SearchResult {
  title: string;
  href: string;
  type: string;
  category: string;
  lastDate?: string;
  organization?: string;
}

function SearchContent() {
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get("q") || "";
  const [query, setQuery] = useState(initialQuery);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchIndex, setSearchIndex] = useState<SearchResult[]>([]);

  useEffect(() => {
    fetch("/search-index.json")
      .then((r) => r.json())
      .then((data) => setSearchIndex(data))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!query.trim() || searchIndex.length === 0) {
      setResults([]);
      return;
    }
    setLoading(true);
    const q = query.toLowerCase();
    const filtered = searchIndex.filter(
      (item) =>
        item.title.toLowerCase().includes(q) ||
        item.organization?.toLowerCase().includes(q) ||
        item.category.toLowerCase().includes(q)
    );
    setResults(filtered.slice(0, 50));
    setLoading(false);
  }, [query, searchIndex]);

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="font-heading text-2xl font-bold text-slate-900 mb-6">Search</h1>

      <form className="flex gap-2 mb-8" onSubmit={(e) => e.preventDefault()}>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search jobs, results, admit cards..."
          className="flex-1 px-4 py-3 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary-900/20 focus:border-primary-900"
          autoFocus
        />
        <button
          type="submit"
          className="px-5 py-3 bg-primary-900 text-white font-semibold rounded-lg text-sm hover:bg-primary-800 transition-colors"
        >
          Search
        </button>
      </form>

      {loading && <p className="text-sm text-slate-500">Searching...</p>}

      {!loading && query && results.length === 0 && (
        <p className="text-sm text-slate-500">No results found for &quot;{query}&quot;</p>
      )}

      {results.length > 0 && (
        <div>
          <p className="text-sm text-slate-500 mb-4">{results.length} results for &quot;{query}&quot;</p>
          <div className="space-y-3">
            {results.map((item, i) => (
              <Link
                key={i}
                href={item.href}
                className="card p-4 block hover:shadow-md transition-shadow group"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-primary-100 text-primary-800 mb-1">
                      {item.type.toUpperCase()}
                    </span>
                    <h3 className="text-sm font-semibold text-slate-900 group-hover:text-primary-900 transition-colors">
                      {item.title}
                    </h3>
                    {item.organization && (
                      <p className="text-xs text-slate-500 mt-0.5">{item.organization}</p>
                    )}
                  </div>
                  {item.lastDate && (
                    <div className="shrink-0 text-right">
                      <div className="text-xs text-slate-400">Last Date</div>
                      <div className="text-xs font-semibold text-slate-700">{item.lastDate}</div>
                    </div>
                  )}
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {!query && (
        <div className="text-center py-16 text-slate-400">
          <div className="text-5xl mb-4">🔍</div>
          <p className="text-sm">Type to search across all jobs, results, and admit cards</p>
        </div>
      )}
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<div className="max-w-4xl mx-auto px-4 py-8 text-center text-slate-400">Loading...</div>}>
      <SearchContent />
    </Suspense>
  );
}
