"use client";

import { useTranslations } from "next-intl";
import {
  fieldDomId,
  fieldErrorKey,
  presentationBody,
  presentationHeading,
  resolveBodyBudget,
  resolveHeadingBudget,
  type EditableCopyField,
} from "@/modules/editorial";

import {
  ContentCopyField,
  CopyLengthCounter,
  EmphasisConventionHint,
} from "./content-phase-copy-field";

import { CONTENT_REVIEW_ID_PREFIX } from "./content-phase-structured-fields";
import { PresentationExtras } from "./content-phase-locale-extras";
import type { ContentLocaleFieldsProps } from "./content-phase-locale-extras";

export { CONTENT_REVIEW_ID_PREFIX };

function CopyField({
  props,
  field,
  value,
}: {
  props: ContentLocaleFieldsProps;
  field: EditableCopyField;
  value: string;
}): React.ReactElement {
  const t = useTranslations("editorialWorkflow.review");
  const { slide, localeKey, policyVersion } = props;
  const budget =
    field === "heading"
      ? resolveHeadingBudget(slide.slide_type, policyVersion)
      : resolveBodyBudget(slide.slide_type, policyVersion);
  const key = fieldErrorKey(slide.slide_index, localeKey, field);
  if (!props.onCopyChange) {
    return (
      <>
        <p
          className={
            field === "heading"
              ? "font-medium text-[var(--color-text)]"
              : "whitespace-pre-wrap text-[var(--color-text-muted)] text-xs"
          }
        >
          {value}
        </p>
        {budget ? <CopyLengthCounter value={value} budget={budget} /> : null}
      </>
    );
  }
  const onCopyChange = props.onCopyChange;
  return (
    <ContentCopyField
      id={fieldDomId(CONTENT_REVIEW_ID_PREFIX, key)}
      label={field === "heading" ? t("headingLabel") : t("bodyLabel")}
      value={value}
      rows={field === "heading" ? 2 : 4}
      localeKey={localeKey}
      budget={budget}
      violations={props.fieldErrors.get(key)}
      onChange={(next) =>
        onCopyChange({
          slideIndex: slide.slide_index,
          locale: localeKey,
          field,
          value: next,
        })
      }
    />
  );
}

/** One locale column of a content-review slide (read-only or editable). */
export function ContentLocaleFields(
  props: ContentLocaleFieldsProps,
): React.ReactElement {
  const t = useTranslations("editorialWorkflow.review");
  const { slide, localeKey, localeLabel } = props;
  const presentation = slide[localeKey];
  const canEdit = props.onCopyChange !== undefined;
  // An editable heading shows what is stored (even empty) so it can be fixed.
  const heading = canEdit
    ? presentationHeading(presentation, "")
    : presentationHeading(presentation, t("untitledSlide"));
  return (
    <div className="space-y-1 rounded-md border border-[var(--color-border)] p-2">
      <p className="font-medium text-[var(--color-text-muted)] text-xs uppercase tracking-wide">
        {localeLabel}
      </p>
      {canEdit ? <EmphasisConventionHint localeKey={localeKey} /> : null}
      <CopyField props={props} field="heading" value={heading} />
      <CopyField
        props={props}
        field="body"
        value={presentationBody(presentation)}
      />
      <PresentationExtras props={props} />
    </div>
  );
}
