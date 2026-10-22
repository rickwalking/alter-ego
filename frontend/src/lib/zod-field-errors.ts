import type { ZodIssue } from "zod";

const PATH_SEPARATOR = ".";

/**
 * Zod issues → `{ "<field.path>": "<i18n key>" }`, first issue per path.
 * ``keyOf`` maps an issue path to its message key; unmapped paths get ``fallback``.
 */
export function fieldErrorsOf(
  issues: readonly ZodIssue[],
  keyOf: (path: readonly PropertyKey[]) => string | undefined,
  fallback: string,
): Record<string, string> {
  const errors: Record<string, string> = {};
  for (const issue of issues) {
    errors[issue.path.join(PATH_SEPARATOR)] ??= keyOf(issue.path) ?? fallback;
  }
  return errors;
}
