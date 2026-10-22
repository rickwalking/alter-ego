import type { Metadata } from "next";
import { MetadataOnlyLayout, pageMetadata } from "@/lib/page-metadata";

/** Page title for the palettes page. */
export function generateMetadata(): Promise<Metadata> {
  return pageMetadata("palettes");
}

export default MetadataOnlyLayout;
