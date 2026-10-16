"use client";

import { useTranslations } from "next-intl";
import {
  formatBudgetUsage,
  isBudgetExceeded,
  presentationBody,
  presentationHeading,
  PRESENTATION_STRUCTURED_ITEM_LIST_KEYS,
  resolveBodyBudget,
} from "@/modules/editorial/workspace/lib/presentation-review-utils";
import type {
  PresentationLocaleKey,
  SlideStructuredItemEdit,
} from "@/modules/editorial/workspace/lib/presentation-slide-resolution";
import {
  fieldDomId,
  fieldErrorKey,
  slideDomId,
  structuredItemFieldPath,
  violationsForSlide,
} from "@/modules/editorial/workspace/lib/slide-field-errors";
import type { LocalizedSlideReview } from "@/modules/editorial/workspace/types-ai";
import { FlaggableTextarea, SlideViolationSummary } from "./slide-field-errors";
import type { SlideCopyEditorProps, StructuredList } from "./types";

const ITEM_BODY_FIELD = "body";

const LOCALE_KEYS: PresentationLocaleKey[] = [
  "presentation_pt",
  "presentation_en",
];

function resolveStructuredList(
  presentation: Record<string, unknown>,
): StructuredList | null {
  for (const listKey of PRESENTATION_STRUCTURED_ITEM_LIST_KEYS) {
    const value = presentation[listKey];
    if (Array.isArray(value) && value.length > 0) {
      return { listKey, items: value as Record<string, unknown>[] };
    }
  }
  return null;
}

function BudgetHint({
  value,
  slideType,
  policyVersion,
}: {
  value: string;
  slideType: string;
  policyVersion?: string | null;
}): React.ReactElement | null {
  const budget = resolveBodyBudget(slideType, policyVersion);
  const usage = formatBudgetUsage(value, budget);
  if (!usage) {
    return null;
  }
  const exceeded = isBudgetExceeded(value, budget);
  return (
    <p
      className={
        exceeded
          ? "text-destructive text-xs"
          : "text-[var(--color-text-muted)] text-xs"
      }
      role={exceeded ? "alert" : undefined}
    >
      {usage}
    </p>
  );
}

function StructuredItemsEditor({
  slide,
  locale,
  onChange,
  props,
}: {
  slide: LocalizedSlideReview;
  locale: PresentationLocaleKey;
  onChange: (edit: SlideStructuredItemEdit) => void;
  props: SlideCopyEditorProps;
}): React.ReactElement | null {
  const t = useTranslations("editorialWorkflow.review");
  const resolved = resolveStructuredList(slide[locale]);
  if (resolved === null) {
    return null;
  }
  return (
    <div className="space-y-1">
      <p className="font-medium text-[var(--color-text-muted)] text-xs">
        {t("structuredItems")}
      </p>
      {resolved.items.map((item, itemIndex) => {
        const key = fieldErrorKey(
          slide.slide_index,
          locale,
          structuredItemFieldPath(resolved.listKey, itemIndex, ITEM_BODY_FIELD),
        );
        return (
          <FlaggableTextarea
            key={key}
            id={fieldDomId(props.idPrefix, key)}
            violations={props.fieldErrors?.get(key)}
            aria-label={t("structuredItemLabel", { index: itemIndex + 1 })}
            value={typeof item.body === "string" ? item.body : ""}
            rows={2}
            onChange={(event) =>
              onChange({
                slideIndex: slide.slide_index,
                locale,
                listKey: resolved.listKey,
                itemIndex,
                field: ITEM_BODY_FIELD,
                value: event.target.value,
              })
            }
          />
        );
      })}
    </div>
  );
}

function LocaleColumn({
  slide,
  localeKey,
  props,
}: {
  slide: LocalizedSlideReview;
  localeKey: PresentationLocaleKey;
  props: SlideCopyEditorProps;
}): React.ReactElement {
  const t = useTranslations("editorialWorkflow.review");
  const presentation = slide[localeKey];
  const localeLabel =
    localeKey === "presentation_pt" ? t("localePt") : t("localeEn");
  const bodyValue = presentationBody(presentation);
  const headingKey = fieldErrorKey(slide.slide_index, localeKey, "heading");
  const bodyKey = fieldErrorKey(slide.slide_index, localeKey, "body");
  return (
    <div className="space-y-1">
      <p className="font-medium text-[var(--color-text-muted)] text-xs uppercase tracking-wide">
        {localeLabel}
      </p>
      <label
        className="font-medium text-[var(--color-text-muted)] text-xs"
        htmlFor={fieldDomId(props.idPrefix, headingKey)}
      >
        {t("headingLabel")}
      </label>
      <FlaggableTextarea
        id={fieldDomId(props.idPrefix, headingKey)}
        violations={props.fieldErrors?.get(headingKey)}
        value={presentationHeading(presentation, "")}
        rows={2}
        onChange={(event) =>
          props.onCopyChange({
            slideIndex: slide.slide_index,
            locale: localeKey,
            field: "heading",
            value: event.target.value,
          })
        }
      />
      <label
        className="font-medium text-[var(--color-text-muted)] text-xs"
        htmlFor={fieldDomId(props.idPrefix, bodyKey)}
      >
        {t("bodyLabel")}
      </label>
      <FlaggableTextarea
        id={fieldDomId(props.idPrefix, bodyKey)}
        violations={props.fieldErrors?.get(bodyKey)}
        value={bodyValue}
        rows={4}
        onChange={(event) =>
          props.onCopyChange({
            slideIndex: slide.slide_index,
            locale: localeKey,
            field: "body",
            value: event.target.value,
          })
        }
      />
      {props.showBudget ? (
        <BudgetHint
          value={bodyValue}
          slideType={slide.slide_type}
          policyVersion={props.policyVersion}
        />
      ) : null}
      {props.onStructuredItemChange ? (
        <StructuredItemsEditor
          slide={slide}
          locale={localeKey}
          onChange={props.onStructuredItemChange}
          props={props}
        />
      ) : null}
    </div>
  );
}

export function SlideCopyEditor(
  props: SlideCopyEditorProps,
): React.ReactElement {
  const t = useTranslations("editorialWorkflow.review");
  const editable =
    props.flagged && props.flagged.size > 0
      ? props.slides.filter((slide) => props.flagged?.has(slide.slide_index))
      : props.slides;

  return (
    <div className="space-y-3">
      {editable.map((slide) => (
        <div
          key={`${props.idPrefix}-${slide.slide_index}`}
          id={slideDomId(props.idPrefix, slide.slide_index)}
          tabIndex={-1}
          className="space-y-2 rounded-md border border-[var(--color-border)] p-2"
        >
          <p className="font-medium text-[var(--color-text)] text-xs">
            {t("slideLabel", { index: slide.slide_index })}
          </p>
          <div className="grid gap-3 md:grid-cols-2">
            {LOCALE_KEYS.map((localeKey) => (
              <LocaleColumn
                key={localeKey}
                slide={slide}
                localeKey={localeKey}
                props={props}
              />
            ))}
          </div>
          <SlideViolationSummary
            slideIndex={slide.slide_index}
            violations={violationsForSlide(
              props.violations ?? [],
              slide.slide_index,
            )}
          />
        </div>
      ))}
    </div>
  );
}
