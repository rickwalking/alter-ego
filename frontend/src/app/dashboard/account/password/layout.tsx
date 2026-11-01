import type { Metadata } from "next";
import { MetadataOnlyLayout, pageMetadata } from "@/lib/page-metadata";

/** Page title for the change-password page. */
export function generateMetadata(): Promise<Metadata> {
  return pageMetadata("changePassword");
}

export default MetadataOnlyLayout;
