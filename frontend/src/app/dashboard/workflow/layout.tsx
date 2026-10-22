import type { Metadata } from "next";
import { MetadataOnlyLayout, pageMetadata } from "@/lib/page-metadata";

/** Page title for the workflow board. */
export function generateMetadata(): Promise<Metadata> {
  return pageMetadata("workflow");
}

export default MetadataOnlyLayout;
