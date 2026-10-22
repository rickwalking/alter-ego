"use client";

import type {
  CopyTextButtonProps,
  LanguageTabsProps,
  PublishPanelProps,
} from "./types";
import type { ViewerLanguage } from "@/modules/publishing/distribution/types";

const VIEWER_LANGUAGES: readonly ViewerLanguage[] = ["pt", "en"];

/**
 * The clipboard rejects in insecure contexts; the rejection is swallowed so the
 * caller still succeeds.
 */
async function copyToClipboard(text: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(text);
  } catch {}
}

/** Copies ``text``; disabled while the text has unsaved edits. */
export function CopyTextButton({
  text,
  label,
  disabled,
}: Readonly<CopyTextButtonProps>): React.ReactElement {
  return (
    <button
      type="button"
      onClick={() => {
        void copyToClipboard(text);
      }}
      disabled={disabled}
      className="rounded-md border border-[var(--color-border)] px-3 py-1.5 text-sm hover:bg-[var(--color-background)] disabled:cursor-not-allowed disabled:opacity-50"
    >
      {label}
    </button>
  );
}

/** PT / EN switch (the viewer and the LinkedIn post share the language). */
export function LanguageTabs({
  language,
  onChange,
  ariaLabel,
  className,
}: Readonly<LanguageTabsProps>): React.ReactElement {
  return (
    <div role="tablist" aria-label={ariaLabel} className={className}>
      {VIEWER_LANGUAGES.map((lang) => (
        <button
          key={lang}
          type="button"
          role="tab"
          aria-selected={language === lang}
          onClick={() => onChange(lang)}
          className={`rounded-md border px-3 py-1 text-xs uppercase ${
            language === lang
              ? "border-[var(--color-primary)] text-[var(--color-primary)]"
              : "border-[var(--color-border)] text-[var(--color-text-muted)]"
          }`}
        >
          {lang}
        </button>
      ))}
    </div>
  );
}

export function PublishResultLine({
  result,
}: Readonly<{
  result: PublishPanelProps["publishResult"];
}>): React.ReactElement | null {
  if (result?.status === "success") {
    return <p className="text-success text-sm">{result.message}</p>;
  }
  if (result?.status === "error") {
    return <p className="text-destructive text-sm">{result.message}</p>;
  }
  return null;
}
