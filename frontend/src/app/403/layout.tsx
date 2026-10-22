import type { Metadata } from "next";
import { MetadataOnlyLayout, pageMetadata } from "@/lib/page-metadata";

/** Page title for the access-denied page. */
export function generateMetadata(): Promise<Metadata> {
  return pageMetadata("forbidden");
}

export default MetadataOnlyLayout;
