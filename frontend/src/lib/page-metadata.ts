import type { Metadata } from "next";
import type { ReactNode } from "react";
import { getTranslations } from "next-intl/server";
import { SITE_DESCRIPTION } from "@/constants/site-metadata";

const PAGE_TITLES_NAMESPACE = "pageTitles";
const SITE_SUFFIX_KEY = "suffix";
const TITLE_SEPARATOR = " · ";
const OG_TYPE_WEBSITE = "website";

/** A page whose `<title>` is defined in the `pageTitles` messages. */
export type PageTitleKey =
  | "blog"
  | "login"
  | "forbidden"
  | "notFound"
  | "dashboard"
  | "calendar"
  | "rubrics"
  | "palettes"
  | "personas"
  | "knowledge"
  | "workflow"
  | "blogPosts"
  | "analytics"
  | "createCarousel"
  | "adminUsers";

/**
 * "<Page> · Pedro Marins" in the interface language, as title and og:title.
 * Next.js replaces the parent's whole `openGraph` with the page's, so this one
 * is complete: og:type, and og:description (the page's description, or the
 * site description the root layout sets).
 */
export async function pageMetadata(
  key: PageTitleKey,
  description?: string,
): Promise<Metadata> {
  const t = await getTranslations(PAGE_TITLES_NAMESPACE);
  const title = `${t(key)}${TITLE_SEPARATOR}${t(SITE_SUFFIX_KEY)}`;
  if (!description) {
    return {
      title,
      openGraph: {
        title,
        description: SITE_DESCRIPTION,
        type: OG_TYPE_WEBSITE,
      },
    };
  }
  return {
    title,
    description,
    openGraph: { title, description, type: OG_TYPE_WEBSITE },
  };
}

/** A layout that only exists to give a client page its metadata. */
export function MetadataOnlyLayout({
  children,
}: Readonly<{ children: ReactNode }>): ReactNode {
  return children;
}
