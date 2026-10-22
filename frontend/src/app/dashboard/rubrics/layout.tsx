import type { Metadata } from "next";
import { MetadataOnlyLayout, pageMetadata } from "@/lib/page-metadata";

/** Page title for the rubrics page. */
export function generateMetadata(): Promise<Metadata> {
  return pageMetadata("rubrics");
}

export default MetadataOnlyLayout;
