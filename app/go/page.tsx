"use client";

import { useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";

function GoContent() {
  const searchParams = useSearchParams();
  const url = searchParams.get("url");

  useEffect(() => {
    if (url) {
      window.location.href = url;
    }
  }, [url]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <div className="text-4xl mb-4">🔗</div>
        <p className="text-slate-600 text-sm">Redirecting to official website...</p>
        {url && (
          <a href={url} className="mt-3 text-primary-900 text-sm underline block" rel="noopener noreferrer">
            Click here if not redirected automatically
          </a>
        )}
      </div>
    </div>
  );
}

export default function GoPage() {
  return (
    <Suspense fallback={<div className="min-h-screen flex items-center justify-center text-slate-400">Redirecting...</div>}>
      <GoContent />
    </Suspense>
  );
}
