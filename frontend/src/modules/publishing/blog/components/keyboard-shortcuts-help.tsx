"use client";

import { useTranslations } from "next-intl";
import { EDITOR_SHORTCUTS } from "@/constants/editor-shortcuts";
import { NeonButton } from "@/components/atoms/neon-button";
import {
  NeonCard,
  NeonCardContent,
  NeonCardHeader,
  NeonCardTitle,
} from "@/components/molecules/neon-card";
import type { KeyboardShortcutsHelpProps } from "./types";

export function KeyboardShortcutsHelp({
  open,
  onClose,
}: KeyboardShortcutsHelpProps) {
  const t = useTranslations("blogEditorial.shortcuts");

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <NeonCard className="w-full max-w-md">
        <NeonCardHeader>
          <NeonCardTitle>{t("title")}</NeonCardTitle>
        </NeonCardHeader>
        <NeonCardContent className="space-y-2">
          {EDITOR_SHORTCUTS.map(({ keys, action }) => (
            <div key={action} className="flex justify-between text-sm">
              <span>{t(`actions.${action}`)}</span>
              <kbd className="rounded border px-2 py-0.5 text-xs">{keys}</kbd>
            </div>
          ))}
          <NeonButton
            className="mt-4 w-full"
            variant="outline"
            onClick={onClose}
          >
            {t("close")}
          </NeonButton>
        </NeonCardContent>
      </NeonCard>
    </div>
  );
}
