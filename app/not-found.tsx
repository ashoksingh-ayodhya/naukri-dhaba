import Link from "next/link";

export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center px-4">
        <div className="text-7xl mb-6">🍽️</div>
        <h1 className="font-heading text-4xl font-bold text-slate-900 mb-3">404</h1>
        <p className="text-slate-600 mb-2 text-lg">Page not found</p>
        <p className="text-slate-400 text-sm mb-8">This page may have moved or the job listing has expired.</p>
        <div className="flex gap-3 justify-center">
          <Link href="/" className="btn-primary">Go Home</Link>
          <Link href="/latest-jobs/" className="btn-secondary">Latest Jobs</Link>
        </div>
      </div>
    </div>
  );
}
