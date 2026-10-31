/** Matches the first Unicode letter (any script, accented letters included). */
const FIRST_LETTER = /\p{L}/u;

/**
 * The avatar initial for a persona name: its first letter, uppercased.
 * Digits, punctuation, symbols and emoji are skipped; a name without any
 * letter returns `null` so the avatar can show an icon instead.
 */
export function personaInitial(name: string): string | null {
  const letter = FIRST_LETTER.exec(name)?.[0];
  return letter ? letter.toLocaleUpperCase() : null;
}
