import { CONTENT_SOURCE_TYPES } from "@/constants/blog-ai";

/** Sources per page of the Knowledge Base carousel-sources tab. */
export const CAROUSEL_SOURCES_PAGE_SIZE = 20;

/** The carousel filter value that lists every carousel. */
export const ALL_CAROUSELS = "";

/** Source types with a translated label (others are shown as they are). */
export const KNOWN_SOURCE_TYPES: readonly string[] =
  Object.values(CONTENT_SOURCE_TYPES);

/** The tabs of the Knowledge Base page. */
export const KNOWLEDGE_TABS = {
  DOCUMENTS: "documents",
  CAROUSEL_SOURCES: "carouselSources",
} as const;
