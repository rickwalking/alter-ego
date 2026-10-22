import type { Metadata } from "next";
import { MetadataOnlyLayout, pageMetadata } from "@/lib/page-metadata";

/** Page title for the user admin. */
export function generateMetadata(): Promise<Metadata> {
  return pageMetadata("adminUsers");
}

export default MetadataOnlyLayout;
