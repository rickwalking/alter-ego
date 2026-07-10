"use client";

import { useTranslations } from "next-intl";
import { NeonBadge } from "@/components/atoms/neon-badge";
import { NeonTextarea } from "@/components/atoms/neon-textarea";
import {
  NeonAlert,
  NeonAlertDescription,
} from "@/components/molecules/neon-alert";
import type {
  EditorialWorkflowState,
  LocalizedSlideReview,
} from "@/modules/publishing";
import { PresentationIconPreview } from "@/modules/editorial";
import { PresentationStructuredItems } from "@/modules/editorial";
import {
  applySlideCopyEdit,
  formatBudgetUsage,
  hasBlockingContentGateValidation,
  hasBlockingPresentationViolations,
  isBudgetExceeded,
  isPresentationStructuredItemList,
  listContentReviewViolations,
  listPresentationIconNames,
  listPresentationStructuredItems,
  listStructuredExtras,
  presentationBody,
  presentationHeading,
  resolveBodyBudget,
  resolveHeadingBudget,
  resolveLocalizedSlides,
  type PresentationLocaleKey,
  type SlideCopyEdit,
} from "@/modules/editorial";

export interface ContentPhaseReviewProps {
  state: EditorialWorkflowState;
  editable?: boolean;
  slides?: LocalizedSlideReview[];
  onSlidesChange?: (slides: LocalizedSlideReview[]) => void;
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

export function ContentPhaseReview({
  state,
  editable = false,
  slides: controlledSlides,
  onSlidesChange,
}: ContentPhaseReviewProps): React.ReactElement {
  const t = useTranslations("editorialWorkflow.review");
  const untitledSlide = t("untitledSlide");
  const baselineSlides = resolveLocalizedSlides(state);
  const localizedSlides = controlledSlides ?? baselineSlides;
  // AE-0309: merge violations arriving in the content interrupt/gate payload
  // with the presentation validation ones (de-duplicated).
  const violations = listContentReviewViolations(state);
  const contentGateBlocked = hasBlockingContentGateValidation(state);
  const approvalBlocked =
    hasBlockingPresentationViolations(state) || contentGateBlocked;
  const promptCount = state.slide_image_prompts?.length ?? 0;
  const canEdit = editable && onSlidesChange !== undefined;

  const handleCopyChange = (edit: SlideCopyEdit): void => {
    if (!onSlidesChange) {
      return;
    }
    onSlidesChange(applySlideCopyEdit(localizedSlides, edit));
  };

  if (localizedSlides.length === 0) {
    return (
      <div className="rounded-md border border-dashed border-[var(--color-border)] p-3 text-[var(--color-text-muted)] text-sm">
        {t("emptyPhase")}
      </div>
    );
  }

  return (
    <div className="space-y-3 rounded-md border border-[var(--color-border)] bg-[var(--color-background)] p-3 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="font-medium">{t("contentTitle")}</p>
        {state.presentation_policy_version ? (
          <NeonBadge variant="outline">
            {t("presentationPolicy", {
              version: state.presentation_policy_version,
            })}
          </NeonBadge>
        ) : null}
      </div>

      {promptCount > 0 ? (
        <p className="text-[var(--color-text-muted)] text-xs">
          {t("imagePromptsLink", { count: promptCount })}
        </p>
      ) : null}

      {contentGateBlocked ? (
        <NeonAlert variant="destructive">
          <NeonAlertDescription>{t("contentGateBlocked")}</NeonAlertDescription>
        </NeonAlert>
      ) : null}

      {approvalBlocked ? (
        <NeonAlert variant="destructive">
          <NeonAlertDescription>
            {t("presentationBlocked")}
          </NeonAlertDescription>
        </NeonAlert>
      ) : null}

      {violations.length > 0 ? (
        <div className="space-y-2 rounded-md border border-destructive/30 bg-destructive/5 p-3">
          <p className="font-medium text-destructive text-xs">
            {t("violationsTitle")}
          </p>
          <ul className="space-y-1 text-destructive text-xs">
            {violations.map((violation) => (
              <li
                key={`${violation.code}-${violation.slide_index ?? "all"}-${violation.field ?? "field"}-${violation.locale ?? "locale"}`}
              >
                <span className="font-mono">{violation.code}</span>
                {violation.slide_index
                  ? ` · ${t("slideLabel", { index: violation.slide_index })}`
                  : ""}
                {violation.locale ? ` · ${violation.locale.toUpperCase()}` : ""}
                {violation.field ? ` · ${violation.field}` : ""}
                {": "}
                {violation.message}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="space-y-3">
        {localizedSlides.map((slide) => {
          const headingBudget = resolveHeadingBudget(
            slide.slide_type,
            state.presentation_policy_version,
          );
          const bodyBudget = resolveBodyBudget(
            slide.slide_type,
            state.presentation_policy_version,
          );
          const renderLocale = (
            localeLabel: string,
            localeKey: PresentationLocaleKey,
            presentation: Record<string, unknown>,
          ) => {
            const heading = presentationHeading(presentation, untitledSlide);
            const body = presentationBody(presentation);
            const structuredExtras = listStructuredExtras(presentation);
            const structuredItems =
              listPresentationStructuredItems(presentation);
            const iconNames = listPresentationIconNames(presentation);
            const headingBudgetLabel = formatBudgetUsage(
              heading,
              headingBudget,
            );
            const bodyBudgetLabel = formatBudgetUsage(body, bodyBudget);
            const headingOverBudget = isBudgetExceeded(heading, headingBudget);
            const bodyOverBudget = isBudgetExceeded(body, bodyBudget);

            return (
              <div className="space-y-1 rounded-md border border-[var(--color-border)] p-2">
                <p className="font-medium text-[var(--color-text-muted)] text-xs uppercase tracking-wide">
                  {localeLabel}
                </p>
                {canEdit ? (
                  <div className="space-y-1">
                    <label
                      className="font-medium text-[var(--color-text-muted)] text-xs"
                      htmlFor={`slide-${slide.slide_index}-${localeKey}-heading`}
                    >
                      {t("headingLabel")}
                    </label>
                    <NeonTextarea
                      id={`slide-${slide.slide_index}-${localeKey}-heading`}
                      value={heading}
                      rows={2}
                      onChange={(event) => {
                        handleCopyChange({
                          slideIndex: slide.slide_index,
                          locale: localeKey,
                          field: "heading",
                          value: event.target.value,
                        });
                      }}
                    />
                  </div>
                ) : (
                  <p className="font-medium text-[var(--color-text)]">
                    {heading}
                  </p>
                )}
                {headingBudgetLabel ? (
                  <p
                    className={
                      headingOverBudget
                        ? "text-destructive text-xs"
                        : "text-[var(--color-text-muted)] text-xs"
                    }
                  >
                    {t("fieldBudget", { usage: headingBudgetLabel })}
                  </p>
                ) : null}
                {canEdit ? (
                  <div className="space-y-1">
                    <label
                      className="font-medium text-[var(--color-text-muted)] text-xs"
                      htmlFor={`slide-${slide.slide_index}-${localeKey}-body`}
                    >
                      {t("bodyLabel")}
                    </label>
                    <NeonTextarea
                      id={`slide-${slide.slide_index}-${localeKey}-body`}
                      value={body}
                      rows={4}
                      onChange={(event) => {
                        handleCopyChange({
                          slideIndex: slide.slide_index,
                          locale: localeKey,
                          field: "body",
                          value: event.target.value,
                        });
                      }}
                    />
                  </div>
                ) : (
                  <p className="whitespace-pre-wrap text-[var(--color-text-muted)] text-xs">
                    {body}
                  </p>
                )}
                {bodyBudgetLabel ? (
                  <p
                    className={
                      bodyOverBudget
                        ? "text-destructive text-xs"
                        : "text-[var(--color-text-muted)] text-xs"
                    }
                  >
                    {t("fieldBudget", { usage: bodyBudgetLabel })}
                  </p>
                ) : null}
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
              </div>
            );
          };

          return (
            <div
              key={`${slide.slide_index}-${slide.slide_type}`}
              className="space-y-2 border-[var(--color-border)] border-b pb-3 last:border-0"
            >
              <div className="flex flex-wrap items-center gap-2">
                <p className="font-medium text-[var(--color-text)]">
                  {t("slideLabel", { index: slide.slide_index })}
                </p>
                <NeonBadge variant="secondary">{slide.slide_type}</NeonBadge>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                {renderLocale(
                  t("localePt"),
                  "presentation_pt",
                  slide.presentation_pt,
                )}
                {renderLocale(
                  t("localeEn"),
                  "presentation_en",
                  slide.presentation_en,
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
