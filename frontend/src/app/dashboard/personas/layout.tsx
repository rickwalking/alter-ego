import type { Metadata } from "next";
import { MetadataOnlyLayout, pageMetadata } from "@/lib/page-metadata";

/** Page title for the personas page. */
export function generateMetadata(): Promise<Metadata> {
  return pageMetadata("personas");
}

export default MetadataOnlyLayout;
