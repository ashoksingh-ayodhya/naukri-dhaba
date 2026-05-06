import fs from "fs";
import path from "path";
import matter from "gray-matter";
import type { PostFrontmatter, PostMeta, ListingPost, PageType } from "./types";

const CONTENT_ROOT = path.join(process.cwd(), "content");

function typeToDir(type: PageType): string {
  const map: Record<PageType, string> = {
    job: "jobs",
    result: "results",
    admit: "admit-cards",
    "answer-key": "answer-keys",
    syllabus: "syllabus",
  };
  return map[type];
}

function slugToHref(type: PageType, category: string, slug: string): string {
  const dir = typeToDir(type);
  if (type === "answer-key" || type === "syllabus") {
    return `/${dir}/${slug}/`;
  }
  return `/${dir}/${category}/${slug}/`;
}

function readMdx(filePath: string): { frontmatter: PostFrontmatter; content: string } {
  const raw = fs.readFileSync(filePath, "utf-8");
  const { data, content } = matter(raw);
  return { frontmatter: data as PostFrontmatter, content };
}

export function getAllPosts(type?: PageType, category?: string): ListingPost[] {
  const posts: ListingPost[] = [];

  const types: PageType[] = type
    ? [type]
    : ["job", "result", "admit", "answer-key", "syllabus"];

  for (const t of types) {
    const dir = path.join(CONTENT_ROOT, typeToDir(t));
    if (!fs.existsSync(dir)) continue;

    if (t === "answer-key" || t === "syllabus") {
      if (!fs.existsSync(dir)) continue;
      const files = fs.readdirSync(dir).filter((f) => f.endsWith(".mdx"));
      for (const file of files) {
        const { frontmatter: fm } = readMdx(path.join(dir, file));
        posts.push({
          title: fm.title,
          slug: fm.slug || file.replace(".mdx", ""),
          type: t,
          category: fm.category || "",
          dept: fm.dept || "",
          organization: fm.organization || "",
          totalPosts: fm.totalPosts,
          lastDate: fm.lastDate,
          publishedAt: fm.publishedAt,
          updatedAt: fm.updatedAt,
          applyUrl: fm.applyUrl,
          href: slugToHref(t, fm.category || "", fm.slug || file.replace(".mdx", "")),
        });
      }
    } else {
      const cats = category
        ? [category]
        : fs.existsSync(dir)
        ? fs.readdirSync(dir).filter((d) => fs.statSync(path.join(dir, d)).isDirectory())
        : [];

      for (const cat of cats) {
        const catDir = path.join(dir, cat);
        if (!fs.existsSync(catDir)) continue;
        const files = fs.readdirSync(catDir).filter((f) => f.endsWith(".mdx"));
        for (const file of files) {
          const { frontmatter: fm } = readMdx(path.join(catDir, file));
          const slug = fm.slug || file.replace(".mdx", "");
          posts.push({
            title: fm.title,
            slug,
            type: t,
            category: cat,
            dept: fm.dept || "",
            organization: fm.organization || "",
            totalPosts: fm.totalPosts,
            lastDate: fm.lastDate,
            publishedAt: fm.publishedAt,
            updatedAt: fm.updatedAt,
            applyUrl: fm.applyUrl,
            href: slugToHref(t, cat, slug),
          });
        }
      }
    }
  }

  return posts.sort((a, b) => {
    const da = a.updatedAt || a.publishedAt;
    const db = b.updatedAt || b.publishedAt;
    return db.localeCompare(da);
  });
}

export function getPost(
  type: PageType,
  category: string,
  slug: string
): { frontmatter: PostFrontmatter; content: string } | null {
  const dir = typeToDir(type);
  let filePath: string;

  if (type === "answer-key" || type === "syllabus") {
    filePath = path.join(CONTENT_ROOT, dir, `${slug}.mdx`);
  } else {
    filePath = path.join(CONTENT_ROOT, dir, category, `${slug}.mdx`);
  }

  if (!fs.existsSync(filePath)) return null;
  return readMdx(filePath);
}

export function getAllPostMeta(type: PageType, category?: string): PostMeta[] {
  const dir = path.join(CONTENT_ROOT, typeToDir(type));
  if (!fs.existsSync(dir)) return [];

  const results: PostMeta[] = [];

  if (type === "answer-key" || type === "syllabus") {
    const files = fs.readdirSync(dir).filter((f) => f.endsWith(".mdx"));
    for (const file of files) {
      const filePath = path.join(dir, file);
      const { frontmatter: fm } = readMdx(filePath);
      results.push({ ...fm, contentPath: filePath });
    }
  } else {
    const cats = category
      ? [category]
      : fs.readdirSync(dir).filter((d) => fs.statSync(path.join(dir, d)).isDirectory());

    for (const cat of cats) {
      const catDir = path.join(dir, cat);
      if (!fs.existsSync(catDir)) continue;
      const files = fs.readdirSync(catDir).filter((f) => f.endsWith(".mdx"));
      for (const file of files) {
        const filePath = path.join(catDir, file);
        const { frontmatter: fm } = readMdx(filePath);
        results.push({ ...fm, contentPath: filePath });
      }
    }
  }

  return results.sort((a, b) => {
    const da = a.updatedAt || a.publishedAt;
    const db = b.updatedAt || b.publishedAt;
    return db.localeCompare(da);
  });
}

export function getLatestPosts(limit = 30): ListingPost[] {
  return getAllPosts().slice(0, limit);
}

export function getLatestByType(type: PageType, limit = 20): ListingPost[] {
  return getAllPosts(type).slice(0, limit);
}

export function isNew(publishedAt: string): boolean {
  const today = new Date();
  const pub = new Date(publishedAt);
  const diffMs = today.getTime() - pub.getTime();
  const diffDays = diffMs / (1000 * 60 * 60 * 24);
  return diffDays <= 3;
}

export function isDeadlineSoon(lastDate: string | undefined): boolean {
  if (!lastDate) return false;
  const [dd, mm, yyyy] = lastDate.split("/");
  if (!dd || !mm || !yyyy) return false;
  const deadline = new Date(`${yyyy}-${mm}-${dd}`);
  const today = new Date();
  const diffMs = deadline.getTime() - today.getTime();
  const diffDays = diffMs / (1000 * 60 * 60 * 24);
  return diffDays >= 0 && diffDays <= 7;
}

export function isExpired(lastDate: string | undefined): boolean {
  if (!lastDate) return false;
  const [dd, mm, yyyy] = lastDate.split("/");
  if (!dd || !mm || !yyyy) return false;
  const deadline = new Date(`${yyyy}-${mm}-${dd}`);
  return deadline < new Date();
}
