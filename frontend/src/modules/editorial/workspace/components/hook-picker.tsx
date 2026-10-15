"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { useSaveCarouselHook } from "@/modules/editorial/workspace/hooks/use-save-hook";
import { HOOK_MAX_LENGTH, HOOK_MAX_WORDS } from "@/constants/create";
import type { HookPickerProps } from "./types";

function hookWordCount(text: string): number {
  return text.trim() ? text.trim().split(/\s+/).length : 0;
}

/**
 * AE-0375: the owner picks one of the generated hooks (or edits it) before
 * approving the outline. The content phase drafts slide 1 with the saved hook.
 */
export function HookPicker({
  projectId,
  candidates,
  initialHook,
  thesisEarly = true,
}: HookPickerProps): React.ReactElement {
  const t = useTranslations("editorialWorkflow.review.hookPicker");
  const save = useSaveCarouselHook();
  const [hook, setHook] = useState(initialHook);
  const words = hookWordCount(hook);
  const invalid = words === 0 || words > HOOK_MAX_WORDS;

  return (
    <div className="space-y-2" data-testid="hook-picker">
      <p className="font-medium">{t("title")}</p>
      {!thesisEarly && (
        <p role="note" className="text-amber-400 text-xs">
          {t("thesisNotEarly")}
        </p>
      )}
      <div role="radiogroup" aria-label={t("title")} className="space-y-1">
        {candidates.map((candidate) => (
          <button
            key={candidate}
            type="button"
            role="radio"
            aria-checked={candidate === hook}
            onClick={() => setHook(candidate)}
            className="block w-full rounded border border-[var(--color-border)] px-2 py-1 text-left text-xs"
          >
            {candidate}
          </button>
        ))}
      </div>
      <label className="block text-[var(--color-text-muted)] text-xs">
        {t("editLabel")}
        <input
          value={hook}
          maxLength={HOOK_MAX_LENGTH}
          onChange={(e) => setHook(e.target.value)}
          className="mt-1 block w-full rounded border border-[var(--color-border)] bg-transparent px-2 py-1 text-sm text-[var(--color-text)]"
        />
      </label>
      <p className="text-[var(--color-text-muted)] text-xs">
        {t("wordCount", { count: words, max: HOOK_MAX_WORDS })}
      </p>
      <NeonButton
        size="sm"
        disabled={invalid || save.isPending}
        onClick={() => save.mutate({ projectId, hookText: hook.trim() })}
      >
        {save.isPending ? t("saving") : t("save")}
      </NeonButton>
      {save.isSuccess && (
        <span role="status" className="text-xs">
          {t("saved")}
        </span>
      )}
      {save.isError && (
        <span role="alert" className="text-destructive text-xs">
          {t("failed")}
        </span>
      )}
    </div>
  );
}
