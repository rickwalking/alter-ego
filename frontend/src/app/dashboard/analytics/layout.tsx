import type { Metadata } from "next";
import { MetadataOnlyLayout, pageMetadata } from "@/lib/page-metadata";

/** Page title for the analytics page. */
export function generateMetadata(): Promise<Metadata> {
  return pageMetadata("analytics");
}

export default MetadataOnlyLayout;
