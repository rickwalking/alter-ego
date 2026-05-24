"use client";

import { useTranslations } from "next-intl";
import { EDITOR_SHORTCUTS } from "@/constants/editor-shortcuts";
import { Button, Card, CardContent, CardHeader, CardTitle } from "@/components/ui";

interface KeyboardShortcutsHelpProps {
  open: boolean;
  onClose: () => void;
}

export function KeyboardShortcutsHelp({ open, onClose }: KeyboardShortcutsHelpProps) {
  const t = useTranslations("blogEditorial.shortcuts");

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>{t("title")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {EDITOR_SHORTCUTS.map(({ keys, action }) => (
            <div key={action} className="flex justify-between text-sm">
              <span>{t(`actions.${action}`)}</span>
              <kbd className="rounded border px-2 py-0.5 text-xs">{keys}</kbd>
            </div>
          ))}
          <Button className="mt-4 w-full" variant="outline" onClick={onClose}>
            {t("close")}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
