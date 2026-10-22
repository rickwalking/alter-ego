"use client";

import { useTranslations } from "next-intl";
import type { CopySaveBarProps } from "./types";

function statusLine(
  props: Readonly<CopySaveBarProps>,
  t: (key: string) => string,
): { text: string; error: boolean } {
  const { status, dirty } = props;
  if (status.kind === "error") {
    return { text: t(status.errorKey), error: true };
  }
  if (dirty) {
    return { text: t("copy.unsaved"), error: false };
  }
  if (status.kind === "saved") {
    return { text: t("copy.saved"), error: false };
  }
  return { text: "", error: false };
}

/**
 * Save button and save state of one publish-panel text. Copy and publish stay
 * disabled while the text is unsaved, which the status line says.
 */
export function CopySaveBar(
  props: Readonly<CopySaveBarProps>,
): React.ReactElement {
  const t = useTranslations("publish");
  const { dirty, status, invalid, onSave } = props;
  const saving = status.kind === "saving";
  const line = statusLine(props, t);
  return (
    <div className="flex flex-wrap items-center gap-3">
      <button
        type="button"
        onClick={() => {
          void onSave();
        }}
        disabled={!dirty || saving || invalid}
        className="rounded-md bg-[var(--color-primary)] px-4 py-1.5 font-medium text-sm text-[var(--color-text)] disabled:cursor-not-allowed disabled:opacity-50"
      >
        {saving ? t("copy.saving") : t("copy.save")}
      </button>
      <p
        role="status"
        aria-live="polite"
        className={`text-xs ${line.error ? "text-destructive" : "text-[var(--color-text-muted)]"}`}
      >
        {line.text}
      </p>
    </div>
  );
}
