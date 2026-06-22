import { getAllPosts } from "@/lib/content";

export const dynamic = "force-static";
export const revalidate = false;

export async function GET() {
  const posts = getAllPosts();
  const index = posts.map((p) => ({
    title: p.title,
    href: p.href,
    type: p.type,
    category: p.category,
    organization: p.organization,
    lastDate: p.lastDate,
  }));
  return Response.json(index);
}
