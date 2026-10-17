"use client";

import { useEffect, useMemo, useRef } from "react";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import { useTranslations } from "next-intl";
import { NeonBadge } from "@/components/atoms/neon-badge";
import { NeonButton } from "@/components/atoms/neon-button";
import {
  NeonAlert,
  NeonAlertDescription,
} from "@/components/molecules/neon-alert";
import type {
  EditorialWorkflowState,
  LocalizedSlideReview,
} from "@/modules/publishing";
import {
  addressViolations,
  applySlideCopyEdit,
  applySlideExtraEdit,
  applySlideStructuredItemEdit,
  BlockingSlidesNotice,
  buildSlideFieldErrors,
  changedLocalizedSlides,
  fieldErrorKey,
  focusInvalidField,
  hasBlockingContentGateValidation,
  hasBlockingPresentationViolations,
  listContentReviewViolations,
  resolveLocalizedSlides,
  slideDomId,
  slidesHaveCopyChanges,
  SlideViolationSummary,
  structuredItemFieldPath,
  useSlideFieldErrors,
  violationsForSlide,
  type SlideCopyEdit,
  type SlideExtraEdit,
  type SlideFieldErrorState,
  type SlideStructuredItemEdit,
} from "@/modules/editorial";
import {
  CONTENT_REVIEW_ID_PREFIX,
  ContentLocaleFields,
} from "./content-phase-locale-fields";
import { ContentViolationList } from "./content-phase-violations";

/**
 * AE-0403: "submit manual fixes" at the content gate. Saves the edits through
 * an edits-only revise (apply + re-validate + re-interrupt); it never approves.
 * AE-0414 (B04): ``onSubmit`` receives only the slides the reviewer changed,
 * each exactly as edited (never clamped to a budget).
 */
export interface ContentManualFixesActions {
  onSubmit: (slides: LocalizedSlideReview[]) => void;
  submitting?: boolean;
}

export interface ContentPhaseReviewProps {
  state: EditorialWorkflowState;
  editable?: boolean;
  slides?: LocalizedSlideReview[];
  onSlidesChange?: (slides: LocalizedSlideReview[]) => void;
  manualFixes?: ContentManualFixesActions;
}

interface ManualFixesFooterProps {
  errors: SlideFieldErrorState;
  canSubmit: boolean;
  manualFixes: ContentManualFixesActions;
  onSubmit: () => void;
}

/** One validation run of the content gate (a resume bumps ``lock_version``). */
function validationStamp(state: EditorialWorkflowState): string {
  return [
    state.lock_version ?? "",
    state.presentation_validation?.validated_at ?? "",
    state.content_gate_validation?.validated_at ?? "",
  ].join("|");
}

function ManualFixesFooter({
  errors,
  canSubmit,
  manualFixes,
  onSubmit,
}: ManualFixesFooterProps): React.ReactElement {
  const t = useTranslations("editorialWorkflow.review");
  return (
    <div className="space-y-2 rounded-md border border-destructive/30 p-3">
      <BlockingSlidesNotice
        message={t("fieldErrors.manualFixesHint")}
        slideIndexes={errors.slideIndexes}
        onSelectSlide={(slideIndex) =>
          focusInvalidField(
            CONTENT_REVIEW_ID_PREFIX,
            errors.fieldErrors,
            slideIndex,
          )
        }
      />
      <NeonButton
        size="sm"
        disabled={!canSubmit || manualFixes.submitting === true}
        onClick={onSubmit}
      >
        {manualFixes.submitting === true
          ? t("fieldErrors.submittingManualFixes")
          : t("fieldErrors.submitManualFixes")}
      </NeonButton>
    </div>
  );
}

export function ContentPhaseReview({
  state,
  editable = false,
  slides: controlledSlides,
  onSlidesChange,
  manualFixes,
}: ContentPhaseReviewProps): React.ReactElement {
  const t = useTranslations("editorialWorkflow.review");
  const baselineSlides = useMemo(() => resolveLocalizedSlides(state), [state]);
  const localizedSlides = controlledSlides ?? baselineSlides;
  // AE-0309: merge violations arriving in the content interrupt/gate payload
  // with the presentation validation ones (de-duplicated).
  const violations = useMemo(() => listContentReviewViolations(state), [state]);
  const addressed = useMemo(() => addressViolations(violations), [violations]);
  const errors = useSlideFieldErrors(addressed, validationStamp(state));
  const awaitingResult = useRef(false);
  const runInProgress =
    state.phase_status === WORKFLOW_PHASE_STATUS.IN_PROGRESS;
  const contentGateBlocked = hasBlockingContentGateValidation(state);
  const approvalBlocked =
    hasBlockingPresentationViolations(state) || contentGateBlocked;
  const promptCount = state.slide_image_prompts?.length ?? 0;
  const canEdit = editable && onSlidesChange !== undefined;

  // AE-0403: once a manual-fix submission comes back (run finished), jump to
  // the first field that is still invalid (a DOM focus, not data fetching).
  useEffect(() => {
    if (!awaitingResult.current || runInProgress) {
      return;
    }
    awaitingResult.current = false;
    focusInvalidField(
      CONTENT_REVIEW_ID_PREFIX,
      buildSlideFieldErrors(addressed),
    );
  }, [addressed, runInProgress]);

  const handleCopyChange = (edit: SlideCopyEdit): void => {
    onSlidesChange?.(applySlideCopyEdit(localizedSlides, edit));
    errors.clearField(fieldErrorKey(edit.slideIndex, edit.locale, edit.field));
  };

  // AE-0414 (B11): structured items and free-text extras are editable too.
  const handleItemChange = (edit: SlideStructuredItemEdit): void => {
    onSlidesChange?.(applySlideStructuredItemEdit(localizedSlides, edit));
    errors.clearField(
      fieldErrorKey(
        edit.slideIndex,
        edit.locale,
        structuredItemFieldPath(edit.listKey, edit.itemIndex, edit.field),
      ),
    );
  };

  const handleExtraChange = (edit: SlideExtraEdit): void => {
    onSlidesChange?.(applySlideExtraEdit(localizedSlides, edit));
    const path = edit.field ? `${edit.extraKey}.${edit.field}` : edit.extraKey;
    errors.clearField(fieldErrorKey(edit.slideIndex, edit.locale, path));
  };

  const submitManualFixes = (): void => {
    if (!manualFixes) {
      return;
    }
    awaitingResult.current = true;
    manualFixes.onSubmit(
      changedLocalizedSlides(baselineSlides, localizedSlides),
    );
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

      <ContentViolationList violations={addressed} />

      <div className="space-y-3">
        {localizedSlides.map((slide) => {
          const localeProps = {
            slide,
            policyVersion: state.presentation_policy_version,
            fieldErrors: errors.fieldErrors,
            onCopyChange: canEdit ? handleCopyChange : undefined,
            onStructuredItemChange: canEdit ? handleItemChange : undefined,
            onExtraChange: canEdit ? handleExtraChange : undefined,
          };

          return (
            <div
              key={`${slide.slide_index}-${slide.slide_type}`}
              id={slideDomId(CONTENT_REVIEW_ID_PREFIX, slide.slide_index)}
              tabIndex={-1}
              className="space-y-2 border-[var(--color-border)] border-b pb-3 last:border-0"
            >
              <div className="flex flex-wrap items-center gap-2">
                <p className="font-medium text-[var(--color-text)]">
                  {t("slideLabel", { index: slide.slide_index })}
                </p>
                <NeonBadge variant="secondary">{slide.slide_type}</NeonBadge>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <ContentLocaleFields
                  {...localeProps}
                  localeKey="presentation_pt"
                  localeLabel={t("localePt")}
                />
                <ContentLocaleFields
                  {...localeProps}
                  localeKey="presentation_en"
                  localeLabel={t("localeEn")}
                />
              </div>
              {canEdit ? (
                <SlideViolationSummary
                  slideIndex={slide.slide_index}
                  violations={violationsForSlide(
                    errors.open,
                    slide.slide_index,
                  )}
                />
              ) : null}
            </div>
          );
        })}
      </div>

      {canEdit && manualFixes && approvalBlocked ? (
        <ManualFixesFooter
          errors={errors}
          canSubmit={slidesHaveCopyChanges(baselineSlides, localizedSlides)}
          manualFixes={manualFixes}
          onSubmit={submitManualFixes}
        />
      ) : null}
    </div>
  );
}
