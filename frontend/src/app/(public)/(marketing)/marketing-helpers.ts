/**
 * Strip lightweight markdown markers from `text` and truncate to at most
 * `maxWords` words, appending an ellipsis when truncated. Behavior is
 * identical to the original inline helper on the marketing home page.
 */
export function truncateWords(text: string, maxWords: number): string {
  const cleaned = text.replace(/\*\*|\*|__|\`|\[|\]|\(|\)/g, "").trim();
  const words = cleaned.split(/\s+/).filter((w) => w.length > 0);
  if (words.length <= maxWords) return cleaned;
  return words.slice(0, maxWords).join(" ") + "...";
}
