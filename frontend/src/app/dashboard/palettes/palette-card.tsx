"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { NeonBadge } from "@/components/atoms/neon-badge";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonCard } from "@/components/molecules/neon-card";
import type { PaletteMode } from "@/schemas/palette";
import { PaletteSwatch } from "./palette-swatch";

export interface PaletteCardProps {
  name: string;
  primary: string;
  accent: string;
  background: string;
  mode: PaletteMode;
  keywords?: readonly string[];
  isRoot: boolean;
  onEdit?: () => void;
  onArchive?: () => void;
  isArchiving?: boolean;
}

const MODE_BADGE_VARIANT: Record<PaletteMode, "teal" | "magenta"> = {
  light: "teal",
  dark: "magenta",
};

export function PaletteCard({
  name,
  primary,
  accent,
  background,
  mode,
  keywords = [],
  isRoot,
  onEdit,
  onArchive,
  isArchiving = false,
}: PaletteCardProps): React.ReactElement {
  const t = useTranslations("palettes");
  const [confirmingArchive, setConfirmingArchive] = useState(false);

  return (
    <NeonCard padding="md" className="flex flex-col gap-3">
      <PaletteSwatch
        primary={primary}
        accent={accent}
        background={background}
        label={name}
      />
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-sm font-semibold text-text-primary break-words">
          {name}
        </h3>
        <div className="flex shrink-0 items-center gap-1.5">
          {isRoot && (
            <NeonBadge variant="cyan" size="sm" outline>
              {t("badge.root")}
            </NeonBadge>
          )}
          <NeonBadge variant={MODE_BADGE_VARIANT[mode]} size="sm">
            {t(`mode.${mode}`)}
          </NeonBadge>
        </div>
      </div>

      {keywords.length > 0 && (
        <ul className="flex flex-wrap gap-1.5" aria-label={t("keywords.label")}>
          {keywords.map((keyword) => (
            <li
              key={keyword}
              className="rounded-full bg-white/5 px-2 py-0.5 text-[11px] text-text-muted"
            >
              {keyword}
            </li>
          ))}
        </ul>
      )}

      {!isRoot && (
        <div className="mt-auto flex items-center justify-end gap-2 pt-1">
          {confirmingArchive ? (
            <>
              <span className="mr-auto text-xs text-text-muted">
                {t("archive.confirm")}
              </span>
              <NeonButton
                variant="ghost"
                size="sm"
                onClick={() => setConfirmingArchive(false)}
              >
                {t("action.cancel")}
              </NeonButton>
              <NeonButton
                variant="danger"
                size="sm"
                loading={isArchiving}
                onClick={onArchive}
              >
                {t("archive.action")}
              </NeonButton>
            </>
          ) : (
            <>
              <NeonButton variant="ghost" size="sm" onClick={onEdit}>
                {t("action.edit")}
              </NeonButton>
              <NeonButton
                variant="secondary"
                size="sm"
                onClick={() => setConfirmingArchive(true)}
              >
                {t("archive.action")}
              </NeonButton>
            </>
          )}
        </div>
      )}
    </NeonCard>
  );
}
