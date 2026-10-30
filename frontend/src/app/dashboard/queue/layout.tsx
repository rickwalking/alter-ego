import type { Metadata } from "next";
import { MetadataOnlyLayout, pageMetadata } from "@/lib/page-metadata";

/** Page title for the generation queue. */
export function generateMetadata(): Promise<Metadata> {
  return pageMetadata("queue");
}

export default MetadataOnlyLayout;
