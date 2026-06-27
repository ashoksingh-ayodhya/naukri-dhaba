export const dynamic = "force-static";

import type { MetadataRoute } from "next";
import { siteConfig, CATEGORIES, STATES } from "@/config/site";
import { getAllPosts } from "@/lib/content";
import { isExpired, parseDDMMYYYY } from "@/lib/dateBadges";

const QUALIFICATION_LEVELS = ["10th-pass", "12th-pass", "diploma", "graduate", "engineering", "postgraduate"];

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
    { url: base + "/about/", changeFrequency: "monthly", priority: 0.4 },
    { url: base + "/privacy/", changeFrequency: "monthly", priority: 0.3 },
    { url: base + "/disclaimer/", changeFrequency: "monthly", priority: 0.3 },
    { url: base + "/contact/", changeFrequency: "monthly", priority: 0.4 },
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
    ...QUALIFICATION_LEVELS.map((level) => ({
      url: `${base}/jobs/qualification/${level}/`,
      changeFrequency: "daily" as const,
      priority: 0.8,
    })),
  ];

  const allPosts = getAllPosts();
  const postRoutes: MetadataRoute.Sitemap = allPosts.map((post) => {
    const d = new Date(post.updatedAt || post.publishedAt);
    // Concentrate crawl budget on live job postings. A job with a real,
    // not-yet-passed deadline is promoted; one whose deadline has passed is
    // de-prioritized (Google for Jobs drops expired postings anyway).
    // Non-job pages and jobs without a parseable deadline keep the neutral
    // default so this only redistributes weight among datable jobs.
    const isJob = post.href.startsWith("/jobs/");
    const hasDeadline = isJob && parseDDMMYYYY(post.lastDate) !== null;
    const live = hasDeadline && !isExpired(post.lastDate);
    const expired = hasDeadline && isExpired(post.lastDate);

    let priority = 0.6;
    let changeFrequency: "daily" | "weekly" | "monthly" = "weekly";
    if (live) {
      priority = 0.8;
      changeFrequency = "daily";
    } else if (expired) {
      priority = 0.3;
      changeFrequency = "monthly";
    }

    return {
      url: `${base}${post.href}`,
      lastModified: isNaN(d.getTime()) ? new Date() : d,
      changeFrequency,
      priority,
    };
  });

  return [...staticRoutes, ...postRoutes];
}
