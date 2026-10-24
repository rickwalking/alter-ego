"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { COVER_PROMPT_COPIED_MS } from "@/constants/cover-prompt-ideas";
import type { CoverPromptCopyProps } from "./types";

/** True once the text is on the clipboard; false when the browser refuses it. */
async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

/**
 * "Copiar" the cover prompt, so it can be used to shoot or generate the photo;
 * says "Copiado" for a moment after a copy. Disabled while the prompt is blank.
 */
export function CoverPromptCopy({
  text,
}: Readonly<CoverPromptCopyProps>): React.ReactElement {
  const t = useTranslations("create.coverIdeas");
  const [copied, setCopied] = useState(false);
  useEffect(() => {
    if (!copied) return undefined;
    const timer = setTimeout(() => setCopied(false), COVER_PROMPT_COPIED_MS);
    return () => clearTimeout(timer);
  }, [copied]);

  return (
    <NeonButton
      variant="ghost"
      size="sm"
      disabled={!text.trim()}
      onClick={() => void copyText(text).then(setCopied)}
    >
      <span aria-live="polite">{copied ? t("copied") : t("copy")}</span>
    </NeonButton>
  );
}
