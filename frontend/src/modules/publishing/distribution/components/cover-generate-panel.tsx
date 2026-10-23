"use client";

import { useCallback, useState } from "react";
import { useTranslations } from "next-intl";
import { NeonConfirmDialog } from "@/components/molecules/neon-confirm-dialog";
import { TEXT_DIM } from "@/constants/neon";
import { ApiError } from "@/lib/api-client";
import { ResourceRequestError } from "@/lib/use-resource-collection";
import {
  GENERATION_STATUS,
  useCoverGenerations,
  useStartCoverGeneration,
  type CoverGenerationInput,
  type CoverGenerations,
} from "@/modules/publishing/distribution/hooks/use-cover-generation";
import {
  CoverGenerationStatus,
  CoverPhotoChecklist,
  CoverPromptField,
  CoverUsageLine,
  generationErrorKey,
} from "./cover-generate-parts";
import type {
  CoverGenerateConfirmProps,
  CoverGeneratePanelProps,
} from "./types";

const MAX_PHOTOS = 3;
const PROMPT_MIN_LENGTH = 3;

type CapReason = "carouselCap" | "monthlyCap" | null;

function capReason(data: CoverGenerations | undefined): CapReason {
  if (!data) {
    return null;
  }
  if (data.carousel_used >= data.carousel_cap) {
    return "carouselCap";
  }
  return data.month_used >= data.month_cap ? "monthlyCap" : null;
}

function apiErrorCode(err: unknown): string | null {
  if (err instanceof ApiError && typeof err.detail === "string") {
    return err.detail;
  }
  return null;
}

/** Tick a photo on and off, keeping at most ``MAX_PHOTOS``. */
function usePhotoSelection(): {
  selected: readonly string[];
  toggle: (assetId: string) => void;
} {
  const [selected, setSelected] = useState<readonly string[]>([]);
  const toggle = useCallback((assetId: string): void => {
    setSelected((current) => {
      if (current.includes(assetId)) {
        return current.filter((id) => id !== assetId);
      }
      return current.length >= MAX_PHOTOS ? current : [...current, assetId];
    });
  }, []);
  return { selected, toggle };
}

/** The form, the caps and the latest generation, with what may happen next. */
function useCoverGenerateForm(projectId: string) {
  const generations = useCoverGenerations(projectId);
  const start = useStartCoverGeneration();
  const { selected, toggle } = usePhotoSelection();
  const [prompt, setPrompt] = useState("");
  const [asking, setAsking] = useState<CoverGenerationInput | null>(null);
  const data = generations.data;
  const latest = data?.generations[0] ?? null;
  const running = latest?.status === GENERATION_STATUS.PENDING;
  const blocked = capReason(data);
  const formReady =
    selected.length > 0 && prompt.trim().length >= PROMPT_MIN_LENGTH;
  const canGenerate =
    formReady && !running && blocked === null && !start.isPending;
  const ask = useCallback((): void => {
    setAsking({ projectId, photoIds: selected, prompt: prompt.trim() });
  }, [projectId, selected, prompt]);
  return {
    data,
    latest,
    running,
    blocked,
    canGenerate,
    selected,
    toggle,
    prompt,
    setPrompt,
    asking,
    setAsking,
    ask,
    start,
  };
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
  const form = useCoverGenerateForm(projectId);
  if (photos.length === 0) {
    return null;
  }
  const confirm = async (): Promise<void> => {
    if (!form.asking) {
      return;
    }
    try {
      await form.start.mutateAsync(form.asking);
    } catch (err) {
      const message = t(generationErrorKey(apiErrorCode(err)));
      const status = err instanceof ApiError ? err.status : 0;
      throw new ResourceRequestError(message, { detail: message, status });
    }
    form.setAsking(null);
  };
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
      <button
        type="button"
        disabled={!form.canGenerate}
        onClick={form.ask}
        className="rounded border border-white/20 px-3 py-1 text-xs disabled:opacity-50"
      >
        {t("action")}
      </button>
      {form.blocked && (
        <p role="note" className="mt-2 text-xs text-amber-300">
          {t(`blocked.${form.blocked}`)}
        </p>
      )}
      <div className="mt-2" aria-live="polite">
        <CoverGenerationStatus
          status={form.latest?.status ?? null}
          errorCode={form.latest?.error_code ?? null}
          canRetry={form.canGenerate}
          onRetry={form.ask}
        />
      </div>
      {form.asking && form.data && (
        <CoverGenerateConfirm
          asking={form.asking}
          usage={form.data}
          onConfirm={confirm}
          onClose={() => form.setAsking(null)}
        />
      )}
    </div>
  );
}
