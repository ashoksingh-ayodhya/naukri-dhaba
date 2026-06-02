export const dynamic = "force-static";

import { getAllPosts } from "@/lib/content";
import { siteConfig } from "@/config/site";

export async function GET() {
  const posts = getAllPosts().slice(0, 100);
  const now = new Date().toUTCString();

  const items = posts
    .map((post) => {
      const url = `${siteConfig.url}${post.href}`;
      const pubDate = post.publishedAt
        ? new Date(post.publishedAt).toUTCString()
        : now;
      const category = post.category.toUpperCase();
      const description = post.lastDate
        ? `Last date: ${post.lastDate}. ${post.totalPosts ? `Vacancies: ${post.totalPosts}.` : ""}`
        : `${category} government job notification.`;

      return `  <item>
    <title><![CDATA[${post.title}]]></title>
    <link>${url}</link>
    <guid isPermaLink="true">${url}</guid>
    <pubDate>${pubDate}</pubDate>
    <category><![CDATA[${category}]]></category>
    <description><![CDATA[${description}]]></description>
  </item>`;
    })
    .join("\n");

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>${siteConfig.name} — Latest Government Jobs</title>
    <link>${siteConfig.url}</link>
    <description>${siteConfig.description}</description>
    <language>en-in</language>
    <lastBuildDate>${now}</lastBuildDate>
    <atom:link href="${siteConfig.url}/feed.xml" rel="self" type="application/rss+xml"/>
    <image>
      <url>${siteConfig.url}/og-default.png</url>
      <title>${siteConfig.name}</title>
      <link>${siteConfig.url}</link>
    </image>
${items}
  </channel>
</rss>`;

  return new Response(xml, {
    headers: {
      "Content-Type": "application/rss+xml; charset=utf-8",
      "Cache-Control": "public, max-age=3600, s-maxage=3600",
    },
  });
}
