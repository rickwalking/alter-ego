import { API_ENDPOINTS } from "@/constants/api";

const SLIDE_FILENAME_PATTERN = /slide_\d+(?:\.jpg)?/;
const PREVIEW_IMAGES_SEGMENT = "/preview/images/";
const PUBLIC_IMAGES_SEGMENT = "/images/";
const LANG_QUERY_PATTERN = /[?&]lang=(pt|en)(?:&|$)/;

/**
 * Map owner-only preview URLs to the public carousel image route.
 *
 * AE-0412 (B08): the public `/images/{file}` route resolves the shared raw
 * image first, then the rendered slide of `?lang=` (same order as the preview
 * route), so the language is kept instead of being dropped.
 */
export function toPublicCarouselImageUrl(url: string): string {
  const [pathOnly = "", query = ""] = url.split("?");
  if (!pathOnly.includes(PREVIEW_IMAGES_SEGMENT)) {
    return pathOnly;
  }
  const publicPath = pathOnly.replace(
    PREVIEW_IMAGES_SEGMENT,
    PUBLIC_IMAGES_SEGMENT,
  );
  const lang = `?${query}`.match(LANG_QUERY_PATTERN)?.[1];
  return lang ? `${publicPath}?lang=${lang}` : publicPath;
}

/** Append a cache-buster without breaking existing query strings. */
export function appendCacheBuster(url: string, version: string): string {
  const separator = url.includes("?") ? "&" : "?";
  return `${url}${separator}v=${encodeURIComponent(version)}`;
}

function slideFilenameFromPath(path: string): string | null {
  const match = path.match(SLIDE_FILENAME_PATTERN);
  if (!match) {
    return null;
  }
  return match[0].endsWith(".jpg") ? match[0] : `${match[0]}.jpg`;
}

/** Map public slide paths to owner-scoped preview routes for draft carousels. */
export function toAuthenticatedPreviewSlideUrl(
  path: string,
  projectId: string,
  language: "pt" | "en",
): string {
  const filename = slideFilenameFromPath(path);
  if (!filename) {
    return path;
  }
  return `${API_ENDPOINTS.CAROUSEL_PREVIEW_IMAGE(projectId, filename)}?lang=${language}`;
}

export interface SlideUrlsForPublishPanelOptions {
  projectId: string;
  paths: string[];
  language: "pt" | "en";
  updatedAt: string;
}

export function slideUrlsForPublishPanel({
  projectId,
  paths,
  language,
  updatedAt,
}: SlideUrlsForPublishPanelOptions): string[] {
  return paths.map((path) =>
    appendCacheBuster(
      toAuthenticatedPreviewSlideUrl(path, projectId, language),
      updatedAt,
    ),
  );
}
