"use client";

import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";

interface PalettesEmptyStateProps {
  onCreate: () => void;
}

/** Teaching empty state for the custom-palette section (roots still render). */
export function PalettesEmptyState({
  onCreate,
}: PalettesEmptyStateProps): React.ReactElement {
  const t = useTranslations("palettes");
  return (
    <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-white/10 px-6 py-10 text-center">
      <p className="text-sm font-semibold text-text-primary">
        {t("empty.title")}
      </p>
      <p className="max-w-sm text-xs text-text-muted">{t("empty.body")}</p>
      <NeonButton variant="primary" size="sm" onClick={onCreate}>
        {t("empty.action")}
      </NeonButton>
    </div>
  );
}
