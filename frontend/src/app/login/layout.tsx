import type { Metadata } from "next";
import { MetadataOnlyLayout, pageMetadata } from "@/lib/page-metadata";

/** Page title for the login page. */
export function generateMetadata(): Promise<Metadata> {
  return pageMetadata("login");
}

export default MetadataOnlyLayout;
