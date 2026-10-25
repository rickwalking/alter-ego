import { useCallback, useState } from "react";
import { HTTP_STATUS } from "@/constants/api";
import { ApiError } from "@/lib/api-client";
import {
  GENERATION_STATUS,
  useCoverGenerations,
  useStartCoverGeneration,
  type CoverGenerations,
} from "./use-cover-generation";
import { ResourceRequestError } from "@/lib/use-resource-collection";
import type {
  CapReason,
  CoverGenerateForm,
  CoverGenerationInput,
  GenerateGate,
} from "./types";

export const MAX_PHOTOS = 3;
const PROMPT_MIN_LENGTH = 3;

function capReason(data: CoverGenerations | undefined): CapReason {
  if (!data) {
    return null;
  }
  if (data.carousel_used >= data.carousel_cap) {
    return "carouselCap";
  }
  if (data.month_used >= data.month_cap) {
    return "monthlyCap";
  }
  if (data.carousel_attempts >= data.carousel_attempt_cap) {
    return "carouselAttempts";
  }
  return data.month_attempts >= data.month_attempt_cap
    ? "monthlyAttempts"
    : null;
}

export function apiErrorCode(err: unknown): string | null {
  if (err instanceof ApiError && typeof err.detail === "string") {
    return err.detail;
  }
  return null;
}

/** Not the owner (403) or the list could not be read. */
export function loadErrorKey(err: Error): string {
  if (err instanceof ApiError && err.status === HTTP_STATUS.FORBIDDEN) {
    return "errors.notOwner";
  }
  return "errors.loadFailed";
}

function withPhoto(
  current: readonly string[],
  assetId: string,
): readonly string[] {
  if (current.includes(assetId) || current.length >= MAX_PHOTOS) {
    return current;
  }
  return [...current, assetId];
}

/** Tick a photo on and off, or add one, keeping at most ``MAX_PHOTOS``. */
function usePhotoSelection(): Pick<
  CoverGenerateForm,
  "selected" | "toggle" | "add"
> {
  const [selected, setSelected] = useState<readonly string[]>([]);
  const toggle = useCallback((assetId: string): void => {
    setSelected((current) =>
      current.includes(assetId)
        ? current.filter((id) => id !== assetId)
        : withPhoto(current, assetId),
    );
  }, []);
  const add = useCallback((assetId: string): void => {
    setSelected((current) => withPhoto(current, assetId));
  }, []);
  return { selected, toggle, add };
}

/** Start the asked generation; a refusal becomes the dialog's message. */
function useConfirmGeneration(
  asking: CoverGenerationInput | null,
  setAsking: (input: CoverGenerationInput | null) => void,
): CoverGenerateForm["confirm"] {
  const start = useStartCoverGeneration();
  return useCallback(
    async (describe: (code: string | null) => string): Promise<void> => {
      if (!asking) {
        return;
      }
      try {
        await start.mutateAsync(asking);
      } catch (err) {
        const message = describe(apiErrorCode(err));
        const status = err instanceof ApiError ? err.status : 0;
        throw new ResourceRequestError(message, { detail: message, status });
      }
      setAsking(null);
    },
    [asking, setAsking, start],
  );
}

function generateAllowed(gate: GenerateGate): boolean {
  return (
    gate.loaded && gate.formReady && !gate.running && gate.blocked === null
  );
}

/**
 * The form, the caps and the latest generation, with what may happen next.
 * Photos are optional: a prompt alone asks for a cover from words.
 */
export function useCoverGenerateForm(projectId: string): CoverGenerateForm {
  const generations = useCoverGenerations(projectId, true);
  const { selected, toggle, add } = usePhotoSelection();
  const [prompt, setPrompt] = useState("");
  const [asking, setAsking] = useState<CoverGenerationInput | null>(null);
  const data = generations.data;
  const latest = data?.generations[0] ?? null;
  const running = latest?.status === GENERATION_STATUS.PENDING;
  const blocked = capReason(data);
  const formReady = prompt.trim().length >= PROMPT_MIN_LENGTH;
  const canGenerate = generateAllowed({
    loaded: data !== undefined,
    formReady,
    running,
    blocked,
  });
  const ask = useCallback((): void => {
    setAsking({ projectId, photoIds: selected, prompt: prompt.trim() });
  }, [projectId, selected, prompt]);
  const confirm = useConfirmGeneration(asking, setAsking);
  return {
    data,
    loadError: generations.error,
    latest,
    running,
    blocked,
    canGenerate,
    selected,
    toggle,
    add,
    prompt,
    setPrompt,
    asking,
    cancel: () => setAsking(null),
    ask,
    confirm,
  };
}
