"use client";

import { useTranslations } from "next-intl";
import {
  fieldDomId,
  fieldErrorKey,
  isPresentationStructuredItemList,
  listPresentationStructuredItems,
  listStructuredExtras,
  PRESENTATION_STRUCTURED_ITEM_LIST_KEYS,
  PresentationStructuredItems,
  presentationBody,
  presentationHeading,
  resolveBodyBudget,
  resolveHeadingBudget,
  type EditableCopyField,
  type PresentationLocaleKey,
  type SlideCopyEdit,
  type SlideExtraEdit,
  type SlideFieldErrors,
  type SlideStructuredItemEdit,
} from "@/modules/editorial";
import type { LocalizedSlideReview } from "@/modules/publishing";
import {
  ContentCopyField,
  CopyLengthCounter,
  EmphasisConventionHint,
} from "./content-phase-copy-field";
import { IconRow, ReadOnlyExtra } from "./content-phase-readonly-extras";
import {
  CONTENT_REVIEW_ID_PREFIX,
  EditableStructuredExtra,
  EditableStructuredItems,
  isEditableExtra,
  type StructuredEditContext,
} from "./content-phase-structured-fields";

export { CONTENT_REVIEW_ID_PREFIX };

export interface ContentLocaleFieldsProps {
  slide: LocalizedSlideReview;
  localeKey: PresentationLocaleKey;
  localeLabel: string;
  /** AE-0414: drives the copy budgets (every policy version has them). */
  policyVersion?: string | null;
  /** Present only while the content step is editable. */
  onCopyChange?: (edit: SlideCopyEdit) => void;
  /** AE-0414 (B11): structured items are editable with the copy. */
  onStructuredItemChange?: (edit: SlideStructuredItemEdit) => void;
  /** AE-0414 (B11): free-text extras (tldr, CTA fields, insight text). */
  onExtraChange?: (edit: SlideExtraEdit) => void;
  fieldErrors: SlideFieldErrors;
}

function structuredList(
  presentation: Record<string, unknown>,
): { listKey: string; items: Record<string, unknown>[] } | null {
  for (const listKey of PRESENTATION_STRUCTURED_ITEM_LIST_KEYS) {
    const value = presentation[listKey];
    if (isPresentationStructuredItemList(value)) {
      return { listKey, items: value as Record<string, unknown>[] };
    }
  }
  return null;
}

function editContext(
  props: ContentLocaleFieldsProps,
): StructuredEditContext | null {
  if (!props.onStructuredItemChange || !props.onExtraChange) {
    return null;
  }
  return {
    slide: props.slide,
    localeKey: props.localeKey,
    policyVersion: props.policyVersion,
    fieldErrors: props.fieldErrors,
    onItemChange: props.onStructuredItemChange,
    onExtraChange: props.onExtraChange,
  };
}

function PresentationExtras({
  props,
}: {
  props: ContentLocaleFieldsProps;
}): React.ReactElement {
  const presentation = props.slide[props.localeKey];
  const context = editContext(props);
  const list = structuredList(presentation);
  const extras = listStructuredExtras(presentation);
  return (
    <>
      {context ? null : (
        <IconRow presentation={presentation} localeLabel={props.localeLabel} />
      )}
      {list && context ? (
        <EditableStructuredItems
          context={context}
          listKey={list.listKey}
          items={list.items}
        />
      ) : null}
      {list && !context ? (
        <PresentationStructuredItems
          items={listPresentationStructuredItems(presentation)}
        />
      ) : null}
      {extras.length > 0 ? (
        <div className="space-y-1 pt-1">
          {extras.map((extra) =>
            context && isEditableExtra(extra.key, extra.value) ? (
              <EditableStructuredExtra
                key={`${props.localeLabel}-${extra.key}`}
                context={context}
                extraKey={extra.key}
                value={extra.value}
              />
            ) : (
              <ReadOnlyExtra
                key={`${props.localeLabel}-${extra.key}`}
                extraKey={extra.key}
                value={extra.value}
              />
            ),
          )}
        </div>
      ) : null}
    </>
  );
}

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
