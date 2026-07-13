"use client";

import { useCallback, useState } from "react";
import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonModal } from "@/components/molecules/neon-modal";
import { TEXT_DIM } from "@/constants/neon";
import { SECTION_CARD_STYLE } from "@/modules/publishing/distribution/constants";
import { useRepublishCarousel } from "@/modules/publishing/distribution/hooks/use-republish-carousel";
import type { RebuildPdfSectionProps } from "./types";

export function RebuildPdfSection({
  projectId,
  onRebuilt,
}: RebuildPdfSectionProps): React.ReactElement {
  const t = useTranslations("publish.rebuildPdf");
  const republish = useRepublishCarousel();
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const openConfirm = useCallback(() => {
    setSuccessMessage(null);
    republish.reset();
    setConfirmOpen(true);
  }, [republish]);

  const handleConfirm = useCallback(() => {
    republish.mutate(
      { projectId },
      {
        onSuccess: (data) => {
          setConfirmOpen(false);
          setSuccessMessage(t("success"));
          onRebuilt(data.artifact_version ?? null);
        },
      },
    );
  }, [projectId, republish, onRebuilt, t]);

  return (
    <div style={SECTION_CARD_STYLE}>
      <h3 className="text-sm font-semibold mb-1">{t("title")}</h3>
      <p className="text-xs mb-3" style={{ color: TEXT_DIM }}>
        {t("description")}
      </p>
      <div className="flex flex-wrap items-center gap-3">
        <NeonButton size="sm" onClick={openConfirm}>
          {t("rebuild")}
        </NeonButton>
        {republish.isError && (
          <span className="text-xs text-red-400" role="alert">
            {republish.error instanceof Error
              ? republish.error.message
              : t("failed")}
          </span>
        )}
        {successMessage && (
          <span className="text-xs text-success" role="status">
            {successMessage}
          </span>
        )}
      </div>

      <NeonModal
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        title={t("confirmTitle")}
        footer={
          <div className="flex justify-end gap-2">
            <NeonButton
              size="sm"
              variant="outline"
              onClick={() => setConfirmOpen(false)}
            >
              {t("cancel")}
            </NeonButton>
            <NeonButton
              size="sm"
              disabled={republish.isPending}
              onClick={handleConfirm}
            >
              {republish.isPending ? t("rebuilding") : t("confirm")}
            </NeonButton>
          </div>
        }
      >
        <p className="text-sm" style={{ color: TEXT_DIM }}>
          {t("confirmBody")}
        </p>
      </NeonModal>
    </div>
  );
}
