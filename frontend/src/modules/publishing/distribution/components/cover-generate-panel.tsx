"use client";

import { useTranslations } from "next-intl";
import { NeonConfirmDialog } from "@/components/molecules/neon-confirm-dialog";
import { TEXT_DIM } from "@/constants/neon";
import {
  MAX_PHOTOS,
  loadErrorKey,
  useCoverGenerateForm,
} from "@/modules/publishing/distribution/hooks/use-cover-generate-form";
import { useCoverPhotoUpload } from "@/modules/publishing/distribution/hooks/use-cover-photo-upload";
import {
  CoverGenerateAction,
  CoverGenerationStatus,
  CoverPhotoChecklist,
  CoverPromptField,
  CoverUsageLine,
  generationErrorKey,
} from "./cover-generate-parts";
import { CoverPhotoUploadField } from "./cover-photo-upload-field";
import type {
  CoverGenerateConfirmProps,
  CoverGenerateOutcomeProps,
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

/**
 * The explicit per-generation consent: names OpenAI (ChatGPT), the photo
 * count and the caps. Without photos it says only the description is sent.
 */
function CoverGenerateConfirm({
  asking,
  usage,
  onConfirm,
  onClose,
}: Readonly<CoverGenerateConfirmProps>): React.ReactElement {
  const t = useTranslations("publish.coverPicker.generate");
  const textOnly = asking.photoIds.length === 0;
  return (
    <NeonConfirmDialog
      title={t(textOnly ? "confirm.textTitle" : "confirm.title")}
      body={t(textOnly ? "confirm.textBody" : "confirm.body", {
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

/** The latest generation's progress or failure, and the confirmation when asked. */
function CoverGenerateOutcome({
  form,
}: Readonly<CoverGenerateOutcomeProps>): React.ReactElement {
  const t = useTranslations("publish.coverPicker.generate");
  return (
    <>
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
    </>
  );
}

/**
 * "Gerar capa com Grok" in the publish-step cover picker. The owner writes a
 * direction in ``CoverPromptField`` and may tick up to three library photos,
 * or upload a new one with "Enviar foto" (it is ticked once stored); with no
 * photo the cover is made from the words alone. Each generation asks for an
 * explicit confirmation that names OpenAI (ChatGPT) and the caps. Progress and
 * failures (with a retry) come from the generation list, polled while one
 * runs; a finished cover appears among the cover options. The form shows only
 * once the list has loaded, which only the owner can read (403 otherwise), so
 * nobody else is offered an upload or a generation.
 */
export function CoverGeneratePanel({
  projectId,
  photos,
  renderPromptSuggestions,
  uploadPhoto,
}: Readonly<CoverGeneratePanelProps>): React.ReactElement | null {
  const t = useTranslations("publish.coverPicker.generate");
  const form = useCoverGenerateForm(projectId);
  const upload = useCoverPhotoUpload({
    projectId,
    upload: uploadPhoto,
    listedIds: photos.map((photo) => photo.asset_id),
    onListed: form.add,
  });
  if (form.loadError) {
    return <CoverGenerateUnavailable error={form.loadError} />;
  }
  if (!form.data) {
    return null;
  }
  return (
    <div className="mt-4 border-t border-white/10 pt-3">
      <h4 className="mb-1 text-xs font-semibold">{t("title")}</h4>
      <p className="mb-3 text-xs" style={{ color: TEXT_DIM }}>
        {t("description")}
      </p>
      {photos.length > 0 && (
        <CoverPhotoChecklist
          photos={photos}
          selected={form.selected}
          max={MAX_PHOTOS}
          disabled={form.running}
          onToggle={form.toggle}
        />
      )}
      <CoverPhotoUploadField upload={upload} disabled={form.running} />
      <CoverPromptField value={form.prompt} onChange={form.setPrompt}>
        {renderPromptSuggestions?.(form.setPrompt)}
      </CoverPromptField>
      <CoverUsageLine usage={form.data} />
      <CoverGenerateAction
        enabled={form.canGenerate && !upload.uploading}
        blocked={form.blocked}
        onAsk={form.ask}
      />
      <CoverGenerateOutcome form={form} />
    </div>
  );
}
