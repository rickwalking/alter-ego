import type { Metadata } from "next";
import { MetadataOnlyLayout, pageMetadata } from "@/lib/page-metadata";

/** Page title for the content calendar. */
export function generateMetadata(): Promise<Metadata> {
  return pageMetadata("calendar");
}

export default MetadataOnlyLayout;
