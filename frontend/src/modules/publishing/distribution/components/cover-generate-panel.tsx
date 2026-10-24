"use client";

import { useTranslations } from "next-intl";
import { NeonConfirmDialog } from "@/components/molecules/neon-confirm-dialog";
import { TEXT_DIM } from "@/constants/neon";
import {
  MAX_PHOTOS,
  loadErrorKey,
  useCoverGenerateForm,
} from "@/modules/publishing/distribution/hooks/use-cover-generate-form";
import {
  CoverGenerateAction,
  CoverGenerationStatus,
  CoverPhotoChecklist,
  CoverPromptField,
  CoverUsageLine,
  generationErrorKey,
} from "./cover-generate-parts";
import type {
  CoverGenerateConfirmProps,
  CoverGeneratePanelProps,
  CoverGenerateUnavailableProps,
} from "./types";

/** Not the owner, or the generation list could not be read: no form. */
function CoverGenerateUnavailable({
  error,
}: Readonly<CoverGenerateUnavailableProps>): React.ReactElement {
  const t = useTranslations("publish.coverPicker.generate");
  return (
    <p role="note" className="mt-4 text-xs" style={{ color: TEXT_DIM }}>
      {t(loadErrorKey(error))}
    </p>
  );
}

/** The explicit per-generation consent: names xAI, the photo count and the caps. */
function CoverGenerateConfirm({
  asking,
  usage,
  onConfirm,
  onClose,
}: Readonly<CoverGenerateConfirmProps>): React.ReactElement {
  const t = useTranslations("publish.coverPicker.generate");
  return (
    <NeonConfirmDialog
      title={t("confirm.title")}
      body={t("confirm.body", {
        count: asking.photoIds.length,
        carouselUsed: usage.carousel_used,
        carouselCap: usage.carousel_cap,
        monthUsed: usage.month_used,
        monthCap: usage.month_cap,
      })}
      confirmLabel={t("confirm.action")}
      cancelLabel={t("confirm.cancel")}
      errorFallback={t("errors.failed")}
      onConfirm={onConfirm}
      onClose={onClose}
    />
  );
}

/**
 * "Gerar capa com Grok" in the publish-step cover picker. The owner ticks up
 * to three library photos and writes a direction in ``CoverPromptField``;
 * each generation asks for an explicit confirmation that names xAI and the
 * caps, because the photos leave the app. Progress and failures (with a retry)
 * come from the generation list, polled while one runs; a finished cover
 * appears among the cover options. Renders nothing without library photos.
 */
export function CoverGeneratePanel({
  projectId,
  photos,
}: Readonly<CoverGeneratePanelProps>): React.ReactElement | null {
  const t = useTranslations("publish.coverPicker.generate");
  const form = useCoverGenerateForm(projectId, photos.length > 0);
  if (photos.length === 0) {
    return null;
  }
  if (form.loadError) {
    return <CoverGenerateUnavailable error={form.loadError} />;
  }
  return (
    <div className="mt-4 border-t border-white/10 pt-3">
      <h4 className="mb-1 text-xs font-semibold">{t("title")}</h4>
      <p className="mb-3 text-xs" style={{ color: TEXT_DIM }}>
        {t("description")}
      </p>
      <CoverPhotoChecklist
        photos={photos}
        selected={form.selected}
        max={MAX_PHOTOS}
        disabled={form.running}
        onToggle={form.toggle}
      />
      <CoverPromptField value={form.prompt} onChange={form.setPrompt} />
      <CoverUsageLine usage={form.data ?? null} />
      <CoverGenerateAction
        enabled={form.canGenerate}
        blocked={form.blocked}
        onAsk={form.ask}
      />
      <div className="mt-2" aria-live="polite">
        <CoverGenerationStatus
          generation={form.latest}
          canRetry={form.canGenerate}
          onRetry={form.ask}
        />
      </div>
      {form.asking && form.data && (
        <CoverGenerateConfirm
          asking={form.asking}
          usage={form.data}
          onConfirm={() => form.confirm((code) => t(generationErrorKey(code)))}
          onClose={form.cancel}
        />
      )}
    </div>
  );
}
