"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonTextarea } from "@/components/atoms/neon-textarea";
import {
  NeonAlert,
  NeonAlertDescription,
} from "@/components/molecules/neon-alert";
import type {
  EditorialWorkflowState,
  LocalizedSlideReview,
  SlideValidationViolation,
} from "@/modules/publishing";
import {
  applySlideCopyEdit,
  isWarningViolation,
  listPresentationViolations,
  presentationBody,
  presentationHeading,
  resolveLocalizedSlides,
  slidesHaveCopyChanges,
  violationToneClasses,
  type PresentationLocaleKey,
  type SlideCopyEdit,
} from "@/modules/editorial";

/** AE-0310: recovery callbacks wired from the workflow panel. */
export interface DesignRecoveryActions {
  onSubmitEditedSlides: (slides: LocalizedSlideReview[]) => void;
  onSendBackToContent: (feedback: string) => void;
  disabled?: boolean;
}

interface DesignRecoveryPanelProps {
  state: EditorialWorkflowState;
  recovery?: DesignRecoveryActions;
}

type RecoveryMode = "idle" | "edit" | "sendBack";

const LOCALE_KEYS: PresentationLocaleKey[] = [
  "presentation_pt",
  "presentation_en",
];

function violationKey(violation: SlideValidationViolation): string {
  return [
    violation.code,
    violation.slide_index ?? "all",
    violation.locale ?? "locale",
    violation.field ?? "field",
  ].join("-");
}

function flaggedSlideIndexes(
  violations: SlideValidationViolation[],
): Set<number> {
  const indexes = new Set<number>();
  for (const violation of violations) {
    if (typeof violation.slide_index === "number") {
      indexes.add(violation.slide_index);
    }
  }
  return indexes;
}

interface ViolationListProps {
  violations: SlideValidationViolation[];
  onSelect: () => void;
  selectHint: string;
  slideLabel: (index: number) => string;
  severityLabel: (violation: SlideValidationViolation) => string;
}

function ViolationList({
  violations,
  onSelect,
  selectHint,
  slideLabel,
  severityLabel,
}: ViolationListProps): React.ReactElement {
  return (
    <ul className="space-y-1 text-xs">
      {violations.map((violation) => (
        <li
          key={violationKey(violation)}
          className={violationToneClasses(violation)}
        >
          <button
            type="button"
            className="text-left underline-offset-2 hover:underline"
            title={selectHint}
            onClick={onSelect}
          >
            <span className="mr-1 font-medium uppercase tracking-wide">
              {severityLabel(violation)}
            </span>
            <span className="font-mono">{violation.code}</span>
            {typeof violation.slide_index === "number"
              ? ` · ${slideLabel(violation.slide_index)}`
              : ""}
            {violation.locale ? ` · ${violation.locale.toUpperCase()}` : ""}
            {violation.field ? ` · ${violation.field}` : ""}
            {": "}
            {violation.message}
          </button>
        </li>
      ))}
    </ul>
  );
}

interface FlaggedSlideEditorProps {
  slides: LocalizedSlideReview[];
  flagged: Set<number>;
  onCopyChange: (edit: SlideCopyEdit) => void;
}

function FlaggedSlideEditor({
  slides,
  flagged,
  onCopyChange,
}: FlaggedSlideEditorProps): React.ReactElement {
  const t = useTranslations("editorialWorkflow.review");
  const editable =
    flagged.size > 0
      ? slides.filter((slide) => flagged.has(slide.slide_index))
      : slides;

  return (
    <div className="space-y-3">
      {editable.map((slide) => (
        <div
          key={`recovery-${slide.slide_index}`}
          className="space-y-2 rounded-md border border-[var(--color-border)] p-2"
        >
          <p className="font-medium text-[var(--color-text)] text-xs">
            {t("slideLabel", { index: slide.slide_index })}
          </p>
          <div className="grid gap-3 md:grid-cols-2">
            {LOCALE_KEYS.map((localeKey) => {
              const presentation = slide[localeKey];
              const localeLabel =
                localeKey === "presentation_pt" ? t("localePt") : t("localeEn");
              return (
                <div key={localeKey} className="space-y-1">
                  <p className="font-medium text-[var(--color-text-muted)] text-xs uppercase tracking-wide">
                    {localeLabel}
                  </p>
                  <label
                    className="font-medium text-[var(--color-text-muted)] text-xs"
                    htmlFor={`recovery-${slide.slide_index}-${localeKey}-heading`}
                  >
                    {t("headingLabel")}
                  </label>
                  <NeonTextarea
                    id={`recovery-${slide.slide_index}-${localeKey}-heading`}
                    value={presentationHeading(presentation, "")}
                    rows={2}
                    onChange={(event) => {
                      onCopyChange({
                        slideIndex: slide.slide_index,
                        locale: localeKey,
                        field: "heading",
                        value: event.target.value,
                      });
                    }}
                  />
                  <label
                    className="font-medium text-[var(--color-text-muted)] text-xs"
                    htmlFor={`recovery-${slide.slide_index}-${localeKey}-body`}
                  >
                    {t("bodyLabel")}
                  </label>
                  <NeonTextarea
                    id={`recovery-${slide.slide_index}-${localeKey}-body`}
                    value={presentationBody(presentation)}
                    rows={4}
                    onChange={(event) => {
                      onCopyChange({
                        slideIndex: slide.slide_index,
                        locale: localeKey,
                        field: "body",
                        value: event.target.value,
                      });
                    }}
                  />
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

interface RecoveryEditSectionProps {
  baselineSlides: LocalizedSlideReview[];
  flagged: Set<number>;
  disabled: boolean;
  onSubmit: (slides: LocalizedSlideReview[]) => void;
  onCancel: () => void;
}

function RecoveryEditSection({
  baselineSlides,
  flagged,
  disabled,
  onSubmit,
  onCancel,
}: RecoveryEditSectionProps): React.ReactElement {
  const tRecovery = useTranslations("editorialWorkflow.review.designRecovery");
  const [editedSlides, setEditedSlides] = useState<LocalizedSlideReview[]>(() =>
    baselineSlides.map((slide) => ({ ...slide })),
  );
  const hasEdits = slidesHaveCopyChanges(baselineSlides, editedSlides);

  const handleCopyChange = (edit: SlideCopyEdit): void => {
    setEditedSlides((slides) => applySlideCopyEdit(slides, edit));
  };

  return (
    <div className="space-y-2">
      <FlaggedSlideEditor
        slides={editedSlides}
        flagged={flagged}
        onCopyChange={handleCopyChange}
      />
      <div className="flex gap-2">
        <NeonButton
          size="sm"
          disabled={disabled || !hasEdits}
          onClick={() => {
            onSubmit(editedSlides);
          }}
        >
          {tRecovery("submitEdits")}
        </NeonButton>
        <NeonButton size="sm" variant="outline" onClick={onCancel}>
          {tRecovery("cancel")}
        </NeonButton>
      </div>
    </div>
  );
}

interface RecoverySendBackSectionProps {
  disabled: boolean;
  onSubmit: (feedback: string) => void;
  onCancel: () => void;
}

function RecoverySendBackSection({
  disabled,
  onSubmit,
  onCancel,
}: RecoverySendBackSectionProps): React.ReactElement {
  const tRecovery = useTranslations("editorialWorkflow.review.designRecovery");
  const [feedback, setFeedback] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (): void => {
    const trimmed = feedback.trim();
    if (!trimmed) {
      setError(tRecovery("sendBackFeedbackRequired"));
      return;
    }
    setError(null);
    onSubmit(trimmed);
  };

  return (
    <div className="space-y-2">
      <label
        className="block font-medium text-xs"
        htmlFor="design-send-back-feedback"
      >
        {tRecovery("sendBackFeedbackLabel")}
      </label>
      <NeonTextarea
        id="design-send-back-feedback"
        value={feedback}
        rows={3}
        placeholder={tRecovery("sendBackFeedbackPlaceholder")}
        onChange={(event) => {
          setFeedback(event.target.value);
          if (error && event.target.value.trim()) {
            setError(null);
          }
        }}
      />
      {error ? <p className="text-destructive text-xs">{error}</p> : null}
      <div className="flex gap-2">
        <NeonButton size="sm" disabled={disabled} onClick={handleSubmit}>
          {tRecovery("sendBackSubmit")}
        </NeonButton>
        <NeonButton size="sm" variant="outline" onClick={onCancel}>
          {tRecovery("cancel")}
        </NeonButton>
      </div>
    </div>
  );
}

export function DesignRecoveryPanel({
  state,
  recovery,
}: DesignRecoveryPanelProps): React.ReactElement {
  const tRecovery = useTranslations("editorialWorkflow.review.designRecovery");
  const t = useTranslations("editorialWorkflow.review");
  const violations = listPresentationViolations(state);
  const baselineSlides = resolveLocalizedSlides(state);
  const [mode, setMode] = useState<RecoveryMode>("idle");
  const flagged = flaggedSlideIndexes(violations);
  const actionsDisabled = recovery?.disabled === true;
  const closeSection = (): void => {
    setMode("idle");
  };

  return (
    <div className="space-y-3">
      <NeonAlert variant="destructive">
        <NeonAlertDescription>
          <span className="block font-medium">{tRecovery("blockedTitle")}</span>
          <span className="block">{tRecovery("hint")}</span>
        </NeonAlertDescription>
      </NeonAlert>

      {violations.length > 0 ? (
        <div className="space-y-2 rounded-md border border-destructive/30 bg-destructive/5 p-3">
          <p className="font-medium text-destructive text-xs">
            {t("violationsTitle")}
          </p>
          <ViolationList
            violations={violations}
            onSelect={() => {
              setMode("edit");
            }}
            selectHint={tRecovery("violationHint")}
            slideLabel={(index) => t("slideLabel", { index })}
            severityLabel={(violation) =>
              isWarningViolation(violation)
                ? t("violationSeverityWarning")
                : t("violationSeverityBlocker")
            }
          />
        </div>
      ) : null}

      {recovery ? (
        <div className="flex flex-wrap gap-2">
          <NeonButton
            size="sm"
            disabled={actionsDisabled}
            onClick={() => {
              setMode("edit");
            }}
          >
            {tRecovery("editAction")}
          </NeonButton>
          <NeonButton
            size="sm"
            disabled={actionsDisabled}
            onClick={() => {
              setMode("sendBack");
            }}
          >
            {tRecovery("sendBackAction")}
          </NeonButton>
        </div>
      ) : null}

      {recovery && mode === "edit" ? (
        <RecoveryEditSection
          baselineSlides={baselineSlides}
          flagged={flagged}
          disabled={actionsDisabled}
          onSubmit={(slides) => {
            recovery.onSubmitEditedSlides(slides);
            closeSection();
          }}
          onCancel={closeSection}
        />
      ) : null}

      {recovery && mode === "sendBack" ? (
        <RecoverySendBackSection
          disabled={actionsDisabled}
          onSubmit={(feedback) => {
            recovery.onSendBackToContent(feedback);
            closeSection();
          }}
          onCancel={closeSection}
        />
      ) : null}
    </div>
  );
}
