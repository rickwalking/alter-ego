"use client";

import { useState } from "react";
import Image from "next/image";
import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonInput } from "@/components/atoms/neon-input";
import { NeonTextarea } from "@/components/atoms/neon-textarea";
import {
  NeonAlert,
  NeonAlertDescription,
} from "@/components/molecules/neon-alert";
import {
  BLOG_EDITOR_ERROR_KINDS,
  BLOG_EDITOR_I18N_NAMESPACE,
  BLOG_IMAGE_PROMPT_MAX_LENGTH,
  BLOG_IMAGE_TEXT_MAX_LENGTH,
} from "@/constants/blog-editor";
import { NEON_RED } from "@/constants/neon";
import { EditorErrorNotice } from "../editor-error-notice";
import type { ImageSlotProps, ImageTextsProps, SlotErrorProps } from "./types";

const LABEL_CLASS = "mb-1 block text-xs font-semibold text-text-muted";
const PROMPT_ROWS = 2;

/** A failed generation reads "failed"; any other error keeps its notice. */
function SlotError({
  error,
  failedText,
}: SlotErrorProps): React.ReactElement | null {
  if (!error) {
    return null;
  }
  if (error.kind !== BLOG_EDITOR_ERROR_KINDS.AI_FAILED) {
    return <EditorErrorNotice error={error} />;
  }
  return (
    <NeonAlert variant="destructive" role="alert">
      <NeonAlertDescription>{failedText}</NeonAlertDescription>
    </NeonAlert>
  );
}

/**
 * Cover / section image slot (AE-0424): generate, regenerate with an edited
 * prompt, remove, and edit alt + caption. A failed generation shows its error
 * on this slot with a retry; the rest of the document stays editable.
 */
export function ImageSlot({
  slotId,
  label,
  image,
  status,
  readOnly,
  issue,
  onGenerate,
  onChange,
}: ImageSlotProps): React.ReactElement {
  const t = useTranslations(BLOG_EDITOR_I18N_NAMESPACE);
  const [prompt, setPrompt] = useState(image?.prompt ?? "");
  const busy = readOnly || status.pending;
  const generate = (): void => onGenerate(prompt.trim() ? prompt.trim() : null);
  return (
    <div
      className="space-y-2 rounded border p-3"
      data-testid={`${slotId}-slot`}
    >
      <p className="text-xs font-semibold">{label}</p>
      {image ? (
        <>
          <div className="relative aspect-video w-full overflow-hidden rounded">
            <Image
              src={image.url}
              alt={image.alt}
              fill
              unoptimized
              className="object-cover"
            />
          </div>
          <ImageTexts
            slotId={slotId}
            image={image}
            readOnly={readOnly}
            issue={issue}
            onChange={onChange}
          />
        </>
      ) : null}
      <label htmlFor={`${slotId}-prompt`} className={LABEL_CLASS}>
        {t("image.prompt")}
      </label>
      <NeonTextarea
        id={`${slotId}-prompt`}
        value={prompt}
        rows={PROMPT_ROWS}
        maxLength={BLOG_IMAGE_PROMPT_MAX_LENGTH}
        placeholder={t("image.promptPlaceholder")}
        disabled={busy}
        onChange={(e) => setPrompt(e.target.value)}
      />
      <SlotError error={status.error} failedText={t("image.failed")} />
      <div className="flex flex-wrap gap-2">
        <NeonButton
          size="sm"
          disabled={busy}
          loading={status.pending}
          onClick={generate}
        >
          {status.error
            ? t("image.retry")
            : image
              ? t("image.regenerate")
              : t("image.generate")}
        </NeonButton>
        {image && (
          <NeonButton
            size="sm"
            variant="outline"
            disabled={busy}
            onClick={() => onChange(null)}
          >
            {t("image.remove")}
          </NeonButton>
        )}
      </div>
    </div>
  );
}

function ImageTexts({
  slotId,
  image,
  readOnly,
  issue,
  onChange,
}: ImageTextsProps): React.ReactElement {
  const t = useTranslations(BLOG_EDITOR_I18N_NAMESPACE);
  const altError = issue ? t(`issues.${issue}`) : null;
  return (
    <div className="grid gap-2 md:grid-cols-2">
      <div>
        <label htmlFor={`${slotId}-alt`} className={LABEL_CLASS}>
          {t("image.alt")}
        </label>
        <NeonInput
          id={`${slotId}-alt`}
          value={image.alt}
          required
          maxLength={BLOG_IMAGE_TEXT_MAX_LENGTH}
          disabled={readOnly}
          aria-invalid={altError ? true : undefined}
          onChange={(e) => onChange({ ...image, alt: e.target.value })}
        />
        {altError && (
          <p role="alert" className="mt-1 text-xs" style={{ color: NEON_RED }}>
            {altError}
          </p>
        )}
      </div>
      <div>
        <label htmlFor={`${slotId}-caption`} className={LABEL_CLASS}>
          {t("image.caption")}
        </label>
        <NeonInput
          id={`${slotId}-caption`}
          value={image.caption ?? ""}
          maxLength={BLOG_IMAGE_TEXT_MAX_LENGTH}
          disabled={readOnly}
          onChange={(e) =>
            onChange({ ...image, caption: e.target.value || null })
          }
        />
      </div>
    </div>
  );
}
