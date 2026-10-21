"use client";

import { useTranslations } from "next-intl";
import { NeonBadge } from "@/components/atoms/neon-badge";
import {
  NeonAlert,
  NeonAlertDescription,
} from "@/components/molecules/neon-alert";
import type {
  EditorialWorkflowState,
  LocalizedSlideReview,
} from "@/modules/publishing";
import {
  slideDomId,
  SlideViolationSummary,
  violationsForSlide,
  type SlideFieldErrorState,
} from "@/modules/editorial";
import {
  CONTENT_REVIEW_ID_PREFIX,
  ContentLocaleFields,
} from "./content-phase-locale-fields";
import type { contentEditHandlers } from "./content-edit-handlers";

/** Title, policy badge, the image-prompt count and the blocking alerts. */
export function ContentReviewHeader({
  policyVersion,
  imagePrompts,
  contentGateBlocked,
  approvalBlocked,
}: Readonly<{
  policyVersion: string | null | undefined;
  imagePrompts: EditorialWorkflowState["slide_image_prompts"];
  contentGateBlocked: boolean;
  approvalBlocked: boolean;
}>): React.ReactElement {
  const t = useTranslations("editorialWorkflow.review");
  const promptCount = imagePrompts?.length ?? 0;
  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="font-medium">{t("contentTitle")}</p>
        {policyVersion ? (
          <NeonBadge variant="outline">
            {t("presentationPolicy", { version: policyVersion })}
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
    </>
  );
}

/** One slide: PT and EN fields side by side (editable when handlers exist). */
export function ContentSlideRow({
  slide,
  policyVersion,
  errors,
  handlers,
}: Readonly<{
  slide: LocalizedSlideReview;
  policyVersion: string | null | undefined;
  errors: SlideFieldErrorState;
  handlers: ReturnType<typeof contentEditHandlers> | null;
}>): React.ReactElement {
  const t = useTranslations("editorialWorkflow.review");
  const localeProps = {
    slide,
    policyVersion,
    fieldErrors: errors.fieldErrors,
    onCopyChange: handlers?.onCopyChange,
    onStructuredItemChange: handlers?.onStructuredItemChange,
    onExtraChange: handlers?.onExtraChange,
    onStructuredListChange: handlers?.onStructuredListChange,
  };
  return (
    <div
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
      {handlers ? (
        <SlideViolationSummary
          slideIndex={slide.slide_index}
          violations={violationsForSlide(errors.open, slide.slide_index)}
        />
      ) : null}
    </div>
  );
}
