"use client";

import { useTranslations } from "next-intl";
import { NeonTextarea } from "@/components/atoms/neon-textarea";
import {
  useFieldErrorMessage,
  useViolationFieldLabel,
} from "@/modules/editorial/workspace/hooks/use-field-error-message";
import { cn } from "@/lib/utils";
import { PRESENTATION_STRUCTURED_ITEM_LIST_KEYS } from "@/modules/editorial/workspace/lib/presentation-review-utils";
import {
  fieldDomId,
  fieldErrorKey,
} from "@/modules/editorial/workspace/lib/slide-field-errors";
import type {
  BlockingSlidesNoticeProps,
  FieldErrorMessageProps,
  FlaggableTextareaProps,
  ListErrorsProps,
  SlideViolationSummaryProps,
} from "./types";

const INVALID_FIELD_CLASS = "border-destructive";
const ERROR_ID_SUFFIX = "-error";

/** The message(s) under one flagged field, wired via aria-describedby. */
export function FieldErrorMessage({
  id,
  violations,
}: Readonly<FieldErrorMessageProps>): React.ReactElement | null {
  const message = useFieldErrorMessage();
  if (!violations || violations.length === 0) {
    return null;
  }
  return (
    <p id={id} className="text-destructive text-xs">
      {violations.map(message).join(" · ")}
    </p>
  );
}

/** A textarea flagged by its violations; the message sits under it. */
export function FlaggableTextarea({
  id,
  violations,
  className,
  ...props
}: Readonly<FlaggableTextareaProps>): React.ReactElement {
  const invalid = (violations?.length ?? 0) > 0;
  const errorId = `${id}${ERROR_ID_SUFFIX}`;
  return (
    <>
      <NeonTextarea
        {...props}
        id={id}
        className={cn(className, invalid && INVALID_FIELD_CLASS)}
        aria-invalid={invalid || undefined}
        aria-describedby={invalid ? errorId : undefined}
      />
      <FieldErrorMessage id={errorId} violations={violations} />
    </>
  );
}

/** "Slide 9 · EN corpo: …" lines at the bottom of a slide form. */
export function SlideViolationSummary({
  slideIndex,
  violations,
}: Readonly<SlideViolationSummaryProps>): React.ReactElement | null {
  const t = useTranslations("editorialWorkflow.review.fieldErrors");
  const message = useFieldErrorMessage();
  const fieldLabel = useViolationFieldLabel();
  if (violations.length === 0) {
    return null;
  }
  return (
    <ul
      className="space-y-0.5 text-destructive text-xs"
      aria-label={t("slideSummary", { slide: slideIndex })}
    >
      {violations.map((violation, index) => (
        <li key={`${violation.code}-${violation.field ?? "slide"}-${index}`}>
          {t("summaryLine", {
            slide: slideIndex,
            field: fieldLabel(violation),
            message: message(violation),
          })}
        </li>
      ))}
    </ul>
  );
}

/** The global blocking line plus one link per still-flagged slide. */
export function BlockingSlidesNotice({
  message,
  slideIndexes,
  onSelectSlide,
}: Readonly<BlockingSlidesNoticeProps>): React.ReactElement {
  const t = useTranslations("editorialWorkflow.review.fieldErrors");
  return (
    <div className="space-y-1 text-destructive text-xs" role="alert">
      <p>{message}</p>
      {slideIndexes.length > 0 ? (
        <p className="flex flex-wrap items-center gap-2">
          <span>{t("slidesToFix")}</span>
          {slideIndexes.map((slideIndex) => (
            <button
              key={slideIndex}
              type="button"
              className="underline"
              onClick={() => onSelectSlide(slideIndex)}
            >
              {t("slideLink", { slide: slideIndex })}
            </button>
          ))}
        </p>
      ) : null}
    </div>
  );
}

const LIST_ERROR_ID_SUFFIX = "-list-error";

/**
 * A list-level violation (``summary_points`` with fewer than 3 complete items),
 * shown under the items heading; adding an item clears it.
 */
export function ListErrors({
  slide,
  locale,
  props,
}: Readonly<ListErrorsProps>): React.ReactElement | null {
  const keys = PRESENTATION_STRUCTURED_ITEM_LIST_KEYS.map((listKey) =>
    fieldErrorKey(slide.slide_index, locale, listKey),
  );
  const violations = keys.flatMap((key) => props.fieldErrors?.get(key) ?? []);
  if (violations.length === 0) {
    return null;
  }
  return (
    <FieldErrorMessage
      id={`${fieldDomId(props.idPrefix, keys[0] ?? "")}${LIST_ERROR_ID_SUFFIX}`}
      violations={violations}
    />
  );
}
