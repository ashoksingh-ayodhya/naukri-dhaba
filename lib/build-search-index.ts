/**
 * Run at build time: `npx ts-node -e "require('./lib/build-search-index')"`
 * Or import from next.config.ts via a plugin.
 * Writes public/search-index.json for client-side search.
 */
import fs from "fs";
import path from "path";
import { getAllPosts } from "./content";

export function buildSearchIndex() {
  const posts = getAllPosts();
  const index = posts.map((p) => ({
    title: p.title,
    href: p.href,
    type: p.type,
    category: p.category,
    organization: p.organization,
    lastDate: p.lastDate,
  }));

  const outPath = path.join(process.cwd(), "public", "search-index.json");
  fs.writeFileSync(outPath, JSON.stringify(index));
  console.log(`Search index: ${index.length} items → ${outPath}`);
}

if (require.main === module) {
  buildSearchIndex();
}
