import { API_ENDPOINTS } from "@/constants/api";

const SLIDE_FILENAME_PATTERN = /slide_\d+(?:\.jpg)?/;

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

export function slideUrlsForPublishPanel(
  projectId: string,
  paths: string[],
  language: "pt" | "en",
  updatedAt: string,
): string[] {
  return paths.map((path) =>
    appendCacheBuster(
      toAuthenticatedPreviewSlideUrl(path, projectId, language),
      updatedAt,
    ),
  );
}
