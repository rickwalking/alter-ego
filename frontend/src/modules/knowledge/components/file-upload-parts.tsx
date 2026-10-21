"use client";

import { useTranslations } from "next-intl";

import { AlertCircle, CheckCircle } from "lucide-react";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonInput } from "@/components/atoms/neon-input";
import { NeonLabel } from "@/components/atoms/neon-label";
import type { UploadMetadataFieldsProps } from "./types";

export function UploadSuccess({
  onDone,
}: {
  onDone?: () => void;
}): React.ReactElement {
  const t = useTranslations("knowledge.upload");
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <CheckCircle className="h-12 w-12 text-success mb-4" />
      <h3 className="text-lg font-semibold">{t("success.title")}</h3>
      <p className="text-sm text-[var(--color-muted-foreground)] mt-1">
        {t("success.description")}
      </p>
      <NeonButton className="mt-4" onClick={onDone}>
        {t("success.done")}
      </NeonButton>
    </div>
  );
}

export function UploadProgressBar({
  progress,
}: {
  progress: number;
}): React.ReactElement {
  const t = useTranslations("knowledge.upload");
  return (
    <div className="space-y-2" role="status" aria-label="Upload progress">
      <div className="flex items-center justify-between text-sm">
        <span className="text-[var(--color-muted-foreground)]">
          {t("uploading")}
        </span>
        <span className="font-medium" aria-live="polite">
          {progress}%
        </span>
      </div>
      <div
        className="h-2 w-full overflow-hidden rounded-full bg-[var(--color-muted)]"
        role="progressbar"
        aria-valuenow={progress}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className="h-full bg-[var(--color-primary)] transition-all duration-300"
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}

export function UploadErrorNotice({
  message,
}: {
  message: string;
}): React.ReactElement {
  const t = useTranslations("knowledge.upload");
  return (
    <div
      className="flex items-center gap-2 rounded-lg border border-[var(--color-destructive)]/20 bg-[var(--color-destructive)]/5 p-3 text-sm text-[var(--color-destructive)]"
      role="alert"
    >
      <AlertCircle className="h-4 w-4 shrink-0" aria-hidden="true" />
      {message || t("error.generic")}
    </div>
  );
}

export function UploadMetadataFields({
  title,
  onTitleChange,
  tags,
  onTagsChange,
  disabled,
}: UploadMetadataFieldsProps): React.ReactElement {
  const t = useTranslations("knowledge.upload");
  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <NeonLabel htmlFor="upload-title">{t("fields.title")}</NeonLabel>
        <NeonInput
          id="upload-title"
          value={title}
          onChange={(e) => onTitleChange(e.target.value)}
          placeholder={t("fields.titlePlaceholder")}
          disabled={disabled}
        />
      </div>
      <div className="space-y-2">
        <NeonLabel htmlFor="upload-tags">{t("fields.tags")}</NeonLabel>
        <NeonInput
          id="upload-tags"
          value={tags}
          onChange={(e) => onTagsChange(e.target.value)}
          placeholder={t("fields.tagsPlaceholder")}
          disabled={disabled}
        />
      </div>
    </div>
  );
}

/** The dashed drop target with the hidden picker and its current content. */
