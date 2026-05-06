import { isNew, isDeadlineSoon, isExpired } from "@/lib/content";

interface StatusBadgeProps {
  publishedAt?: string;
  lastDate?: string;
}

export function StatusBadge({ publishedAt, lastDate }: StatusBadgeProps) {
  if (publishedAt && isNew(publishedAt)) {
    return <span className="badge-new">NEW</span>;
  }
  if (lastDate && isExpired(lastDate)) {
    return <span className="badge-closed">Closed</span>;
  }
  if (lastDate && isDeadlineSoon(lastDate)) {
    return <span className="badge-soon">Closing Soon</span>;
  }
  return <span className="badge-active">Active</span>;
}

interface CategoryBadgeProps {
  category: string;
  dept?: string;
}

export function CategoryBadge({ category, dept }: CategoryBadgeProps) {
  const label = dept || category.toUpperCase();
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-primary-100 text-primary-800">
      {label}
    </span>
  );
}
