import type { Metadata } from "next";
import { MetadataOnlyLayout, pageMetadata } from "@/lib/page-metadata";

/** Page title for the carousel creation pages. */
export function generateMetadata(): Promise<Metadata> {
  return pageMetadata("createCarousel");
}

export default MetadataOnlyLayout;
