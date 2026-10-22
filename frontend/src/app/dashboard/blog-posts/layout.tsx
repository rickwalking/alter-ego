import type { Metadata } from "next";
import { MetadataOnlyLayout, pageMetadata } from "@/lib/page-metadata";

/** Page title for the blog posts list and editor. */
export function generateMetadata(): Promise<Metadata> {
  return pageMetadata("blogPosts");
}

export default MetadataOnlyLayout;
