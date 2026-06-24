"use client";

import { useState, type KeyboardEvent } from "react";
import { useTranslations } from "next-intl";
import { NeonInput } from "@/components/atoms/neon-input";

interface PaletteKeywordsFieldProps {
  keywords: readonly string[];
  onAdd: (raw: string) => void;
  onRemove: (keyword: string) => void;
}

/** Comma/Enter chip entry for AUTO-detection keywords (mirrors the backend guard). */
export function PaletteKeywordsField({
  keywords,
  onAdd,
  onRemove,
}: PaletteKeywordsFieldProps): React.ReactElement {
  const t = useTranslations("palettes");
  const [draft, setDraft] = useState("");

  const commit = (): void => {
    onAdd(draft);
    setDraft("");
  };

  const handleKey = (e: KeyboardEvent<HTMLInputElement>): void => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      commit();
    }
  };

  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor="palette-keywords" className="text-xs text-text-muted">
        {t("form.keywords")}
      </label>
      <NeonInput
        id="palette-keywords"
        value={draft}
        autoComplete="off"
        placeholder={t("form.keywordsPlaceholder")}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={handleKey}
        onBlur={commit}
      />
      <p className="text-[11px] text-text-dim">{t("form.keywordsHint")}</p>
      {keywords.length > 0 && (
        <ul className="flex flex-wrap gap-1.5 pt-1">
          {keywords.map((keyword) => (
            <li key={keyword}>
              <button
                type="button"
                onClick={() => onRemove(keyword)}
                className="rounded-full bg-white/5 px-2 py-0.5 text-[11px] text-text-muted transition-colors hover:bg-neon-red/20 hover:text-neon-red"
                aria-label={t("form.removeKeyword", { keyword })}
              >
                {keyword} ×
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
