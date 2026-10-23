"use client";

import Link from "next/link";
import { useState } from "react";
import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";
import type { PhotoInUseCarousel } from "@/modules/editorial";

export interface CreatePhotoDeleteProps {
  selectedId: string;
  onDelete: (photoId: string) => void;
  deleting: boolean;
  blockedBy: readonly PhotoInUseCarousel[] | null;
  failed: boolean;
}

/**
 * "Excluir foto selecionada" with an inline confirm. A photo a carousel still
 * uses is not deleted: the carousels are listed, each linking to its workspace.
 */
export function CreatePhotoDelete({
  selectedId,
  onDelete,
  deleting,
  blockedBy,
  failed,
}: Readonly<CreatePhotoDeleteProps>): React.ReactElement | null {
  const t = useTranslations("create.photo.delete");
  const [confirming, setConfirming] = useState(false);
  if (!selectedId) {
    return null;
  }

  const confirmDelete = (): void => {
    setConfirming(false);
    onDelete(selectedId);
  };

  return (
    <div className="mt-3 flex flex-col gap-2">
      {confirming ? (
        <div
          role="group"
          aria-label={t("confirm")}
          className="flex flex-col gap-2"
        >
          <p className="text-xs text-text-muted">{t("confirm")}</p>
          <div className="flex flex-wrap gap-2">
            <NeonButton
              variant="ghost"
              size="sm"
              onClick={() => setConfirming(false)}
            >
              {t("cancel")}
            </NeonButton>
            <NeonButton variant="danger" size="sm" onClick={confirmDelete}>
              {t("confirmAction")}
            </NeonButton>
          </div>
        </div>
      ) : (
        <div>
          <NeonButton
            variant="ghost"
            size="sm"
            loading={deleting}
            onClick={() => setConfirming(true)}
          >
            {deleting ? t("deleting") : t("action")}
          </NeonButton>
        </div>
      )}
      {blockedBy !== null && (
        <div role="alert" className="text-xs text-amber-300">
          <p>{t("inUse")}</p>
          <ul className="mt-1 list-disc pl-4">
            {blockedBy.map((carousel) => (
              <li key={carousel.id}>
                <Link
                  href={DASHBOARD_ROUTES.CREATE_WORKSPACE(carousel.id)}
                  className="underline"
                >
                  {carousel.title ?? t("untitled")}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}
      {failed && blockedBy === null && (
        <p role="alert" className="text-xs text-red-400">
          {t("failed")}
        </p>
      )}
    </div>
  );
}
