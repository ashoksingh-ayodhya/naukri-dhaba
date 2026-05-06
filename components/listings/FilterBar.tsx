import Link from "next/link";
import { CATEGORIES } from "@/config/site";

interface FilterBarProps {
  baseHref: string;
  activeCategory?: string;
  showAll?: boolean;
}

export default function FilterBar({ baseHref, activeCategory, showAll = true }: FilterBarProps) {
  return (
    <div className="flex flex-wrap gap-2 mb-4">
      {showAll && (
        <Link
          href={baseHref}
          className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
            !activeCategory
              ? "bg-primary-900 text-white"
              : "bg-white text-slate-600 border border-slate-200 hover:border-primary-300 hover:text-primary-900"
          }`}
        >
          All
        </Link>
      )}
      {CATEGORIES.map((cat) => (
        <Link
          key={cat.slug}
          href={`${baseHref}${cat.slug}/`}
          className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
            activeCategory === cat.slug
              ? "bg-primary-900 text-white"
              : "bg-white text-slate-600 border border-slate-200 hover:border-primary-300 hover:text-primary-900"
          }`}
        >
          {cat.label}
        </Link>
      ))}
    </div>
  );
}
