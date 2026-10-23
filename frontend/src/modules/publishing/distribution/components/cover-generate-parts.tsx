"use client";

import Image from "next/image";
import { useTranslations } from "next-intl";
import { API_ENDPOINTS } from "@/constants/api";
import { BG_CARD, NEON_CYAN, TEXT_DIM } from "@/constants/neon";
import { GENERATION_STATUS } from "@/modules/publishing/distribution/hooks/use-cover-generation";
import type {
  CoverGenerateActionProps,
  CoverGenerationStatusProps,
  CoverPhotoChecklistProps,
  CoverPromptFieldProps,
  CoverUsageLineProps,
} from "./types";

const THUMB_WIDTH = 56;
const THUMB_HEIGHT = 70;
const IDLE_BORDER = "1px solid rgba(255,255,255,0.08)";
const PROMPT_MAX_LENGTH = 500;

/** Failure codes with their own sentence; anything else reads as "failed". */
export const GENERATION_ERROR_KEYS: Readonly<Record<string, string>> = {
  cover_generation_bridge_failed: "errors.bridge",
  cover_generation_invalid_image: "errors.invalidImage",
  cover_generation_interrupted: "errors.interrupted",
  cover_generation_photo_unreadable: "errors.photoUnreadable",
  cover_generation_in_progress: "errors.inProgress",
  cover_generation_carousel_cap: "errors.carouselCap",
  cover_generation_monthly_cap: "errors.monthlyCap",
  cover_generation_unavailable: "errors.unavailable",
  cover_generation_photo_not_allowed: "errors.photoNotAllowed",
  cover_generation_not_owner: "errors.notOwner",
};
const GENERIC_ERROR_KEY = "errors.failed";

/** The i18n key of an API or generation failure code. */
export function generationErrorKey(code: string | null | undefined): string {
  return (code && GENERATION_ERROR_KEYS[code]) ?? GENERIC_ERROR_KEY;
}

/**
 * The owner's library photos as checkboxes with thumbnails. Once ``max`` are
 * ticked the others are disabled.
 */
export function CoverPhotoChecklist({
  photos,
  selected,
  max,
  disabled,
  onToggle,
}: Readonly<CoverPhotoChecklistProps>): React.ReactElement {
  const t = useTranslations("publish.coverPicker.generate");
  const full = selected.length >= max;
  return (
    <fieldset className="mb-3">
      <legend className="mb-2 text-xs" style={{ color: TEXT_DIM }}>
        {t("photosLegend", { max })}
      </legend>
      <div className="flex flex-wrap gap-2">
        {photos.map((photo, index) => {
          const checked = selected.includes(photo.asset_id);
          return (
            <label
              key={photo.asset_id}
              className="flex cursor-pointer flex-col items-center gap-1 text-[11px]"
              style={{ color: checked ? NEON_CYAN : TEXT_DIM }}
            >
              <span
                style={{
                  width: `${THUMB_WIDTH}px`,
                  height: `${THUMB_HEIGHT}px`,
                  borderRadius: "6px",
                  background: BG_CARD,
                  border: checked ? `2px solid ${NEON_CYAN}` : IDLE_BORDER,
                  overflow: "hidden",
                }}
              >
                <Image
                  src={API_ENDPOINTS.CREATOR_ASSET_IMAGE(photo.asset_id)}
                  alt=""
                  width={THUMB_WIDTH}
                  height={THUMB_HEIGHT}
                  className="h-full w-full object-cover"
                  unoptimized
                />
              </span>
              <input
                type="checkbox"
                checked={checked}
                disabled={disabled || (full && !checked)}
                onChange={() => onToggle(photo.asset_id)}
                aria-label={t("photoLabel", { number: index + 1 })}
              />
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

/** "Gerando…" while the latest generation runs; its failure with a retry. */
export function CoverGenerationStatus({
  status,
  errorCode,
  canRetry,
  onRetry,
}: Readonly<CoverGenerationStatusProps>): React.ReactElement | null {
  const t = useTranslations("publish.coverPicker.generate");
  if (status === GENERATION_STATUS.PENDING) {
    return (
      <p role="status" className="text-xs" style={{ color: NEON_CYAN }}>
        {t("pending")}
      </p>
    );
  }
  if (status === GENERATION_STATUS.SUCCEEDED) {
    return (
      <p role="status" className="text-xs text-success">
        {t("succeeded")}
      </p>
    );
  }
  if (status !== GENERATION_STATUS.FAILED) {
    return null;
  }
  return (
    <div role="alert" className="text-xs text-red-400">
      <span>{t(generationErrorKey(errorCode))}</span>{" "}
      {canRetry && (
        <button type="button" className="underline" onClick={onRetry}>
          {t("retry")}
        </button>
      )}
    </div>
  );
}

/**
 * The direction for the generated cover (editable). ``children`` render under
 * the field, e.g. prompt suggestions that call ``onChange`` to fill it.
 */
export function CoverPromptField({
  value,
  onChange,
  children,
}: Readonly<CoverPromptFieldProps>): React.ReactElement {
  const t = useTranslations("publish.coverPicker.generate");
  return (
    <div className="mb-2">
      <label className="block text-xs" style={{ color: TEXT_DIM }}>
        {t("promptLabel")}
        <textarea
          value={value}
          maxLength={PROMPT_MAX_LENGTH}
          rows={2}
          placeholder={t("promptPlaceholder")}
          onChange={(e) => onChange(e.target.value)}
          className="mt-1 block w-full rounded border border-white/10 bg-transparent p-2 text-xs"
        />
      </label>
      {children}
    </div>
  );
}

/** "1 de 4 neste carrossel · 3 de 40 no mês" once the caps are known. */
export function CoverUsageLine({
  usage,
}: Readonly<CoverUsageLineProps>): React.ReactElement | null {
  const t = useTranslations("publish.coverPicker.generate");
  if (!usage) {
    return null;
  }
  return (
    <p className="mb-2 text-[11px]" style={{ color: TEXT_DIM }}>
      {t("usage", {
        carouselUsed: usage.carousel_used,
        carouselCap: usage.carousel_cap,
        monthUsed: usage.month_used,
        monthCap: usage.month_cap,
      })}
    </p>
  );
}

/** "Gerar capa", and why it is disabled when a cap is reached. */
export function CoverGenerateAction({
  enabled,
  blocked,
  onAsk,
}: Readonly<CoverGenerateActionProps>): React.ReactElement {
  const t = useTranslations("publish.coverPicker.generate");
  return (
    <>
      <button
        type="button"
        disabled={!enabled}
        onClick={onAsk}
        className="rounded border border-white/20 px-3 py-1 text-xs disabled:opacity-50"
      >
        {t("action")}
      </button>
      {blocked && (
        <p role="note" className="mt-2 text-xs text-amber-300">
          {t(`blocked.${blocked}`)}
        </p>
      )}
    </>
  );
}
