import { siteConfig } from "@/config/site";
import { buildBreadcrumbJsonLd, buildListingPageJsonLd } from "@/lib/seo";
import type { ListingPost } from "@/lib/types";

/** CollectionPage + ItemList + BreadcrumbList for any listing page. */
export default function ListingSchema({
  title,
  path,
  posts,
  crumbs,
}: {
  title: string;
  path: string;
  posts: ListingPost[];
  crumbs: Array<{ label: string; href?: string }>;
}) {
  const url = `${siteConfig.url}${path}`;
  const items = posts.slice(0, 50).map((p) => ({ name: p.title, url: `${siteConfig.url}${p.href}` }));
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(buildListingPageJsonLd(title, url, items)) }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(buildBreadcrumbJsonLd(crumbs)) }}
      />
    </>
  );
}
