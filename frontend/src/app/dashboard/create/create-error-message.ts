import { HTTP_STATUS } from "@/constants/api";
import { ApiError } from "@/lib/api-client";

/**
 * Turn a failed `POST /api/carousels` into one readable line
 * instead of "HTTP error! status: 422". FastAPI validation errors name the
 * field (`loc`) and the rule (`type`, `ctx`); each field is reported once.
 */

type Translate = (
  key: string,
  values?: Record<string, string | number>,
) => string;

interface ValidationIssue {
  loc?: unknown;
  type?: unknown;
  msg?: unknown;
  ctx?: { max_length?: unknown; min_length?: unknown } | null;
}

const ISSUE_TOO_LONG = "string_too_long";
const ISSUE_TOO_SHORT = "string_too_short";
const ISSUE_MISSING = "missing";
const ISSUE_SEPARATOR = " · ";

/** Request fields the form can name (create.errors.fields.*). */
const KNOWN_FIELDS: ReadonlySet<string> = new Set([
  "topic",
  "audience",
  "niche",
  "custom_visual_details",
  "pov_thesis",
  "pov_personal_proof",
  "hook_asset_id",
]);

function fieldOf(issue: ValidationIssue): string {
  const loc: readonly unknown[] = Array.isArray(issue.loc) ? issue.loc : [];
  const last = loc[loc.length - 1];
  return typeof last === "string" ? last : "";
}

function describeIssue(issue: ValidationIssue, t: Translate): string {
  const field = fieldOf(issue);
  const label = KNOWN_FIELDS.has(field) ? t(`errors.fields.${field}`) : field;
  const max = issue.ctx?.max_length;
  if (issue.type === ISSUE_TOO_LONG && typeof max === "number") {
    return t("errors.tooLong", { field: label, max });
  }
  if (issue.type === ISSUE_TOO_SHORT || issue.type === ISSUE_MISSING) {
    return t("errors.required", { field: label });
  }
  const message = typeof issue.msg === "string" ? issue.msg : "";
  return t("errors.invalid", { field: label, message });
}

function describeValidation(detail: unknown, t: Translate): string | null {
  if (!Array.isArray(detail) || detail.length === 0) {
    return null;
  }
  const lines = (detail as ValidationIssue[]).map((issue) =>
    describeIssue(issue, t),
  );
  return [...new Set(lines)].join(ISSUE_SEPARATOR);
}

/** One readable, localized line for a create-carousel failure. */
export function createErrorMessage(error: unknown, t: Translate): string {
  if (!(error instanceof ApiError)) {
    return t("errors.createFailed");
  }
  if (error.status === HTTP_STATUS.UNPROCESSABLE_ENTITY) {
    return describeValidation(error.detail, t) ?? t("errors.validation");
  }
  if (typeof error.detail === "string" && error.detail.trim()) {
    return t("errors.createFailedDetail", { detail: error.detail });
  }
  return t("errors.createFailed");
}
