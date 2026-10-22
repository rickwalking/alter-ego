import type { Metadata } from "next";
import { MetadataOnlyLayout, pageMetadata } from "@/lib/page-metadata";

/** Page title for the knowledge base. */
export function generateMetadata(): Promise<Metadata> {
  return pageMetadata("knowledge");
}

export default MetadataOnlyLayout;
