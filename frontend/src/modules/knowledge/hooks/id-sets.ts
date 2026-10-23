/** The empty id set. */
export const NO_IDS: ReadonlySet<string> = new Set();

/** `ids` plus `id`. */
export function withId(
  ids: ReadonlySet<string>,
  id: string,
): ReadonlySet<string> {
  return new Set(ids).add(id);
}

/** `ids` without `id`. */
export function withoutId(
  ids: ReadonlySet<string>,
  id: string,
): ReadonlySet<string> {
  const next = new Set(ids);
  next.delete(id);
  return next;
}
