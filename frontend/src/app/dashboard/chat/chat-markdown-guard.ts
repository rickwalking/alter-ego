/** Deeper list or quote nesting than this renders as plain text. */
export const CHAT_MARKDOWN_MAX_NESTING = 20;

/** Longer replies than this render as plain text. */
export const CHAT_MARKDOWN_MAX_LENGTH = 20_000;

/** Spaces of indentation that open one more nested list level. */
const INDENT_PER_LEVEL = 2;

const QUOTE_MARKER = ">";
const BULLET_MARKERS = new Set(["-", "*", "+"]);

function isBlank(char: string | undefined): boolean {
  return char === " " || char === "\t";
}

function isDigit(char: string | undefined): boolean {
  return char !== undefined && char >= "0" && char <= "9";
}

/** A quote marker, or a bullet followed by a blank, at ``index``. */
function isSingleCharMarker(line: string, index: number): boolean {
  const char = line[index] ?? "";
  if (char === QUOTE_MARKER) return true;
  return BULLET_MARKERS.has(char) && isBlank(line[index + 1]);
}

/** Length of an ordered-list marker (`12.` or `3)`) at ``index``, else 0. */
function orderedMarkerLength(line: string, index: number): number {
  let end = index;
  while (isDigit(line[end])) end += 1;
  const closes = line[end] === "." || line[end] === ")";
  return end > index && closes && isBlank(line[end + 1]) ? end - index + 1 : 0;
}

/** Container markers (quote, bullet, ordered) opened at the start of ``line``. */
function lineNesting(line: string): number {
  let index = 0;
  let levels = 0;
  let indent = 0;
  while (index < line.length) {
    const ordered = orderedMarkerLength(line, index);
    if (isBlank(line[index])) {
      indent += levels === 0 ? 1 : 0;
      index += 1;
    } else if (isSingleCharMarker(line, index)) {
      levels += 1;
      index += 1;
    } else if (ordered > 0) {
      levels += 1;
      index += ordered;
    } else {
      break;
    }
  }
  return levels + Math.floor(indent / INDENT_PER_LEVEL);
}

/**
 * Whether a reply is safe to hand to the markdown parser: not too long and
 * not nested deeper than the renderer's recursion can take (a crafted
 * `- - - …` or `>>>…` reply would otherwise overflow the call stack).
 */
export function isRenderableMarkdown(text: string): boolean {
  if (text.length > CHAT_MARKDOWN_MAX_LENGTH) return false;
  return text
    .split("\n")
    .every((line) => lineNesting(line) <= CHAT_MARKDOWN_MAX_NESTING);
}
