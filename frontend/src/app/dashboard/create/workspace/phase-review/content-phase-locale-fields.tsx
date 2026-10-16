"use client";

import { useTranslations } from "next-intl";
import {
  fieldDomId,
  fieldErrorKey,
  FlaggableTextarea,
  formatBudgetUsage,
  isBudgetExceeded,
  isPresentationStructuredItemList,
  listPresentationIconNames,
  listPresentationStructuredItems,
  listStructuredExtras,
  PresentationIconPreview,
  PresentationStructuredItems,
  presentationBody,
  presentationHeading,
  type EditableCopyField,
  type PresentationFieldBudget,
  type PresentationLocaleKey,
  type SlideCopyEdit,
  type SlideFieldErrors,
} from "@/modules/editorial";
import type { LocalizedSlideReview } from "@/modules/publishing";

/** AE-0403: content-review DOM ids (``slide-{n}-{locale}-{field}``). */
export const CONTENT_REVIEW_ID_PREFIX = "slide";

export interface ContentLocaleFieldsProps {
  slide: LocalizedSlideReview;
  localeKey: PresentationLocaleKey;
  localeLabel: string;
  budgets: {
    heading: PresentationFieldBudget | null;
    body: PresentationFieldBudget | null;
  };
  /** Present only while the content step is editable. */
  onCopyChange?: (edit: SlideCopyEdit) => void;
  fieldErrors: SlideFieldErrors;
}

interface EditableCopyProps {
  props: ContentLocaleFieldsProps;
  field: EditableCopyField;
  value: string;
  rows: number;
}

function EditableCopy({
  props,
  field,
  value,
  rows,
}: EditableCopyProps): React.ReactElement {
  const t = useTranslations("editorialWorkflow.review");
  const { slide, localeKey } = props;
  const key = fieldErrorKey(slide.slide_index, localeKey, field);
  const id = fieldDomId(CONTENT_REVIEW_ID_PREFIX, key);
  return (
    <div className="space-y-1">
      <label
        className="font-medium text-[var(--color-text-muted)] text-xs"
        htmlFor={id}
      >
        {field === "heading" ? t("headingLabel") : t("bodyLabel")}
      </label>
      <FlaggableTextarea
        id={id}
        violations={props.fieldErrors.get(key)}
        value={value}
        rows={rows}
        onChange={(event) => {
          props.onCopyChange?.({
            slideIndex: slide.slide_index,
            locale: localeKey,
            field,
            value: event.target.value,
          });
        }}
      />
    </div>
  );
}

function BudgetLine({
  value,
  budget,
}: {
  value: string;
  budget: PresentationFieldBudget | null;
}): React.ReactElement | null {
  const t = useTranslations("editorialWorkflow.review");
  const usage = formatBudgetUsage(value, budget);
  if (!usage) {
    return null;
  }
  return (
    <p
      className={
        isBudgetExceeded(value, budget)
          ? "text-destructive text-xs"
          : "text-[var(--color-text-muted)] text-xs"
      }
    >
      {t("fieldBudget", { usage })}
    </p>
  );
}

function formatStructuredValue(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }
  return JSON.stringify(value, null, 2);
}

function renderStructuredExtraValue(value: unknown): React.ReactNode {
  if (isPresentationStructuredItemList(value)) {
    return <PresentationStructuredItems items={value} />;
  }
  if (typeof value === "string" && value.trim()) {
    return (
      <p className="whitespace-pre-wrap text-[var(--color-text-muted)] text-xs">
        {value}
      </p>
    );
  }
  return (
    <pre className="whitespace-pre-wrap font-mono text-[var(--color-text-muted)] text-xs">
      {formatStructuredValue(value)}
    </pre>
  );
}

function PresentationExtras({
  presentation,
  localeLabel,
}: {
  presentation: Record<string, unknown>;
  localeLabel: string;
}): React.ReactElement {
  const t = useTranslations("editorialWorkflow.review");
  const structuredExtras = listStructuredExtras(presentation);
  const structuredItems = listPresentationStructuredItems(presentation);
  const iconNames = listPresentationIconNames(presentation);
  return (
    <>
      {iconNames.length > 0 ? (
        <div className="flex flex-wrap items-center gap-2 pt-1">
          {iconNames.map((iconName) => (
            <div
              key={`${localeLabel}-${iconName}`}
              className="inline-flex items-center gap-1 rounded border border-[var(--color-border)] px-2 py-1 text-xs"
            >
              <PresentationIconPreview
                iconName={iconName}
                className="h-3.5 w-3.5 text-[var(--color-text)]"
              />
              <span className="font-mono text-[var(--color-text-muted)]">
                {iconName}
              </span>
            </div>
          ))}
        </div>
      ) : null}
      {structuredItems.length > 0 ? (
        <PresentationStructuredItems items={structuredItems} />
      ) : null}
      {structuredExtras.length > 0 ? (
        <div className="space-y-1 pt-1">
          {structuredExtras.map((extra) => (
            <div key={`${localeLabel}-${extra.key}`}>
              <p className="font-medium text-[var(--color-text-muted)] text-xs">
                {t("structuredExtra", { field: extra.key })}
              </p>
              {renderStructuredExtraValue(extra.value)}
            </div>
          ))}
        </div>
      ) : null}
    </>
  );
}

/** One locale column of a content-review slide (read-only or editable). */
export function ContentLocaleFields(
  props: ContentLocaleFieldsProps,
): React.ReactElement {
  const t = useTranslations("editorialWorkflow.review");
  const { slide, localeKey, localeLabel, budgets } = props;
  const presentation = slide[localeKey];
  const heading = presentationHeading(presentation, t("untitledSlide"));
  const body = presentationBody(presentation);
  const canEdit = props.onCopyChange !== undefined;
  return (
    <div className="space-y-1 rounded-md border border-[var(--color-border)] p-2">
      <p className="font-medium text-[var(--color-text-muted)] text-xs uppercase tracking-wide">
        {localeLabel}
      </p>
      {canEdit ? (
        <EditableCopy props={props} field="heading" value={heading} rows={2} />
      ) : (
        <p className="font-medium text-[var(--color-text)]">{heading}</p>
      )}
      <BudgetLine value={heading} budget={budgets.heading} />
      {canEdit ? (
        <EditableCopy props={props} field="body" value={body} rows={4} />
      ) : (
        <p className="whitespace-pre-wrap text-[var(--color-text-muted)] text-xs">
          {body}
        </p>
      )}
      <BudgetLine value={body} budget={budgets.body} />
      <PresentationExtras
        presentation={presentation}
        localeLabel={localeLabel}
      />
    </div>
  );
}
