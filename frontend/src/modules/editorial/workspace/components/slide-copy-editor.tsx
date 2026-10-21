"use client";

import { useTranslations } from "next-intl";
import {
  presentationBody,
  presentationHeading,
} from "@/modules/editorial/workspace/lib/presentation-review-utils";

import type { PresentationLocaleKey } from "@/modules/editorial/workspace/lib/presentation-slide-resolution";
import {
  fieldDomId,
  fieldErrorKey,
  slideDomId,
  violationsForSlide,
} from "@/modules/editorial/workspace/lib/slide-field-errors";
import type { LocalizedSlideReview } from "@/modules/editorial/workspace/types-ai";
import { FlaggableTextarea, SlideViolationSummary } from "./slide-field-errors";
import type { SlideCopyEditorProps } from "./types";
import { BudgetHint, StructuredItemsEditor } from "./slide-copy-editor-items";

const LOCALE_KEYS: PresentationLocaleKey[] = [
  "presentation_pt",
  "presentation_en",
];

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
