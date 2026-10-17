import { stripEmphasisMarkup } from "@/lib/public-blog-text";

const LINK_MARKERS_PATTERN = /\[|\]|\(|\)/g;

/**
 * Strip lightweight markdown markers (and, AE-0412, emphasis HTML) from `text` and truncate to at most
 * `maxWords` words, appending an ellipsis when truncated. Behavior is
 * identical to the original inline helper on the marketing home page.
 */
export function truncateWords(text: string, maxWords: number): string {
  const cleaned = stripEmphasisMarkup(text.replace(LINK_MARKERS_PATTERN, ""));
  const words = cleaned.split(/\s+/).filter((w) => w.length > 0);
  if (words.length <= maxWords) return cleaned;
  return words.slice(0, maxWords).join(" ") + "...";
}
