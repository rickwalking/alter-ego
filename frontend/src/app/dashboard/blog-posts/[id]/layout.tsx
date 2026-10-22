import type { ReactNode } from "react";

import { API_ENDPOINTS } from "@/constants/api";
import { notFoundUnlessOwnerResource } from "@/lib/owner-resource";

/** An unknown or malformed blog post id answers the not-found page (HTTP 404). */
export default async function BlogPostLayout({
  children,
  params,
}: Readonly<{
  children: ReactNode;
  params: Promise<{ id: string }>;
}>): Promise<ReactNode> {
  const { id } = await params;
  await notFoundUnlessOwnerResource(id, API_ENDPOINTS.BLOG_POST_BY_ID);
  return children;
}
