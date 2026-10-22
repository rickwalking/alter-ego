import type { Metadata } from "next";
import type { ReactNode } from "react";
import { getTranslations } from "next-intl/server";

const PAGE_TITLES_NAMESPACE = "pageTitles";
const SITE_SUFFIX_KEY = "suffix";
const TITLE_SEPARATOR = " · ";

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

/** "<Page> · Pedro Marins" in the interface language, as title and og:title. */
export async function pageMetadata(key: PageTitleKey): Promise<Metadata> {
  const t = await getTranslations(PAGE_TITLES_NAMESPACE);
  const title = `${t(key)}${TITLE_SEPARATOR}${t(SITE_SUFFIX_KEY)}`;
  return { title, openGraph: { title } };
}

/** A layout that only exists to give a client page its metadata. */
export function MetadataOnlyLayout({
  children,
}: Readonly<{ children: ReactNode }>): ReactNode {
  return children;
}
