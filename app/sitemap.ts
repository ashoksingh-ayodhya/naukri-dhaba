export const dynamic = "force-static";

import type { MetadataRoute } from "next";
import { siteConfig, CATEGORIES, STATES } from "@/config/site";
import { getAllPosts } from "@/lib/content";

export default function sitemap(): MetadataRoute.Sitemap {
  const base = siteConfig.url;

  const staticRoutes: MetadataRoute.Sitemap = [
    { url: base + "/", changeFrequency: "daily", priority: 1.0 },
    { url: base + "/latest-jobs/", changeFrequency: "daily", priority: 0.9 },
    { url: base + "/results/", changeFrequency: "daily", priority: 0.9 },
    { url: base + "/admit-cards/", changeFrequency: "daily", priority: 0.9 },
    { url: base + "/answer-keys/", changeFrequency: "weekly", priority: 0.8 },
    { url: base + "/syllabus/", changeFrequency: "weekly", priority: 0.7 },
    { url: base + "/search/", changeFrequency: "monthly", priority: 0.6 },
    ...CATEGORIES.map((cat) => ({
      url: `${base}/jobs/${cat.slug}/`,
      changeFrequency: "daily" as const,
      priority: 0.8,
    })),
    ...CATEGORIES.map((cat) => ({
      url: `${base}/results/${cat.slug}/`,
      changeFrequency: "daily" as const,
      priority: 0.7,
    })),
    ...CATEGORIES.map((cat) => ({
      url: `${base}/admit-cards/${cat.slug}/`,
      changeFrequency: "daily" as const,
      priority: 0.7,
    })),
    ...STATES.map((state) => ({
      url: `${base}/state/${state.slug}/`,
      changeFrequency: "daily" as const,
      priority: 0.7,
    })),
  ];

  const allPosts = getAllPosts();
  const postRoutes: MetadataRoute.Sitemap = allPosts.map((post) => ({
    url: `${base}${post.href}`,
    lastModified: new Date(post.updatedAt || post.publishedAt),
    changeFrequency: "weekly" as const,
    priority: 0.6,
  }));

  return [...staticRoutes, ...postRoutes];
}
