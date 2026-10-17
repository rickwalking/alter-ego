"use client";

import { useTranslations } from "next-intl";
import {
  isWarningViolation,
  useFieldErrorMessage,
  useViolationFieldLabel,
  violationToneClasses,
  type SlideValidationViolation,
} from "@/modules/editorial";

/**
 * The content gate's violation list. AE-0414 (B24): each line shows the
 * translated message and field label (pt/en) instead of the backend's English
 * message and raw field path; unknown codes keep the backend message.
 */
export function ContentViolationList({
  violations,
}: {
  violations: SlideValidationViolation[];
}): React.ReactElement | null {
  const t = useTranslations("editorialWorkflow.review");
  const message = useFieldErrorMessage();
  const fieldLabel = useViolationFieldLabel();
  if (violations.length === 0) {
    return null;
  }
  return (
    <div className="space-y-2 rounded-md border border-destructive/30 bg-destructive/5 p-3">
      <p className="font-medium text-destructive text-xs">
        {t("violationsTitle")}
      </p>
      <ul className="space-y-1 text-xs">
        {violations.map((violation) => {
          const label = fieldLabel(violation);
          return (
            <li
              key={`${violation.code}-${violation.slide_index ?? "all"}-${violation.field ?? "field"}-${violation.locale ?? "locale"}`}
              className={violationToneClasses(violation)}
            >
              <span className="mr-1 font-medium uppercase tracking-wide">
                {isWarningViolation(violation)
                  ? t("violationSeverityWarning")
                  : t("violationSeverityBlocker")}
              </span>
              {violation.slide_index
                ? `${t("slideLabel", { index: violation.slide_index })} · `
                : ""}
              {label ? `${label}: ` : ""}
              {message(violation)}
              {" · "}
              <span className="font-mono text-[var(--color-text-muted)]">
                {violation.code}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
