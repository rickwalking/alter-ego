/** Matches the first Unicode letter with its combining marks (any script). */
const FIRST_LETTER = /\p{L}\p{M}*/u;

/**
 * Fixed locale for uppercasing, so the server and the browser agree (a
 * Turkish runtime would turn "i" into "İ" and break hydration).
 */
const INITIAL_CASE_LOCALE = "en";

/** Composed form, so "e" + combining acute becomes a single "é". */
const COMPOSED_FORM = "NFC";

/**
 * The avatar initial for a persona name: its first letter (with its accents),
 * uppercased. Digits, punctuation, symbols and emoji are skipped; a letter
 * whose uppercase is longer than itself (e.g. "ß" → "SS") is kept as is; a
 * name without any letter returns `null` so the avatar can show an icon.
 */
export function personaInitial(name: string): string | null {
  const letter = FIRST_LETTER.exec(name.normalize(COMPOSED_FORM))?.[0];
  if (!letter) {
    return null;
  }
  const upper = letter
    .toLocaleUpperCase(INITIAL_CASE_LOCALE)
    .normalize(COMPOSED_FORM);
  return upper.length === letter.length ? upper : letter;
}
