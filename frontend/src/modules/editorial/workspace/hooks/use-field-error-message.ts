import { useCallback } from "react";
import { useTranslations } from "next-intl";
import {
  EMPHASIS_TAG_EXAMPLE,
  FIELD_ERROR_LIMIT_CODES,
  FIELD_ERROR_MESSAGE_CODES,
} from "@/modules/editorial/workspace/constants";
import { violationLimit } from "@/modules/editorial/workspace/lib/slide-field-errors";
import type { SlideValidationViolation } from "@/modules/editorial/workspace/types-ai";

const FIELD_LABEL_KEYS: Readonly<Record<string, string>> = {
  heading: "fields.heading",
  body: "fields.body",
  title: "fields.title",
  icon_name: "fields.icon",
};

const LOCALE_LABEL_KEYS: Readonly<Record<string, string>> = {
  pt: "locales.pt",
  en: "locales.en",
};

/**
 * A violation's human pt/en message. Known codes are translated (the
 * length codes with the backend ``max N`` limit); any other code, or a length
 * code whose limit is missing, falls back to the backend message.
 */
export function useFieldErrorMessage(): (
  violation: SlideValidationViolation,
) => string {
  const t = useTranslations("editorialWorkflow.review.fieldErrors");
  return useCallback(
    (violation: SlideValidationViolation): string => {
      if (!FIELD_ERROR_MESSAGE_CODES.has(violation.code)) {
        return violation.message;
      }
      const limit = violationLimit(violation);
      if (FIELD_ERROR_LIMIT_CODES.has(violation.code) && limit === null) {
        return violation.message;
      }
      return t(`codes.${violation.code}`, {
        limit: limit ?? 0,
        tag: EMPHASIS_TAG_EXAMPLE,
      });
    },
    [t],
  );
}

/** "EN corpo" / "PT item 2 · título" for a per-slide summary line. */
export function useViolationFieldLabel(): (
  violation: SlideValidationViolation,
) => string {
  const t = useTranslations("editorialWorkflow.review.fieldErrors");
  return useCallback(
    (violation: SlideValidationViolation): string => {
      const localeKey = LOCALE_LABEL_KEYS[violation.locale ?? ""];
      const locale = localeKey ? t(localeKey) : "";
      const fieldKey =
        FIELD_LABEL_KEYS[violation.item_field ?? violation.field ?? ""];
      const field = fieldKey ? t(fieldKey) : (violation.field ?? "");
      const label =
        typeof violation.item_index === "number"
          ? t("fields.item", { index: violation.item_index + 1, field })
          : field;
      return [locale, label].filter(Boolean).join(" ");
    },
    [t],
  );
}
