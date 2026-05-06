import Link from "next/link";

interface Crumb {
  label: string;
  href?: string;
}

export default function Breadcrumb({ crumbs }: { crumbs: Crumb[] }) {
  return (
    <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-sm text-slate-500 flex-wrap">
      {crumbs.map((crumb, i) => (
        <span key={i} className="flex items-center gap-1.5">
          {i > 0 && <span className="text-slate-300">/</span>}
          {crumb.href ? (
            <Link href={crumb.href} className="hover:text-primary-900 transition-colors">
              {crumb.label}
            </Link>
          ) : (
            <span className="text-slate-700 font-medium truncate max-w-xs">{crumb.label}</span>
          )}
        </span>
      ))}
    </nav>
  );
}
