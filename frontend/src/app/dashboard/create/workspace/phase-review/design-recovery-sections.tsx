"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonTextarea } from "@/components/atoms/neon-textarea";

import type {
  LocalizedSlideReview,
  SlideValidationViolation,
} from "@/modules/publishing";
import {
  applySlideCopyEdit,
  SlideCopyEditor,
  slidesHaveCopyChanges,
  violationToneClasses,
  type SlideCopyEdit,
} from "@/modules/editorial";

export function violationKey(violation: SlideValidationViolation): string {
  return [
    violation.code,
    violation.slide_index ?? "all",
    violation.locale ?? "locale",
    violation.field ?? "field",
  ].join("-");
}

export interface ViolationListProps {
  violations: SlideValidationViolation[];
  onSelect: () => void;
  selectHint: string;
  slideLabel: (index: number) => string;
  severityLabel: (violation: SlideValidationViolation) => string;
}

export function ViolationList({
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

export interface RecoveryEditSectionProps {
  baselineSlides: LocalizedSlideReview[];
  flagged: Set<number>;
  disabled: boolean;
  onSubmit: (slides: LocalizedSlideReview[]) => void;
  onCancel: () => void;
}

export function RecoveryEditSection({
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
      <SlideCopyEditor
        slides={editedSlides}
        idPrefix="recovery"
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

export interface RecoverySendBackSectionProps {
  disabled: boolean;
  onSubmit: (feedback: string) => void;
  onCancel: () => void;
}

export function RecoverySendBackSection({
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
