"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonModal } from "@/components/molecules/neon-modal";
import { NEON_RED } from "@/constants/neon";
import { ResourceRequestError } from "@/lib/use-resource-collection";
import type { QualityRubric } from "@/modules/quality";

interface RubricDeleteDialogProps {
  rubric: QualityRubric;
  onConfirm: () => Promise<void>;
  onClose: () => void;
}

/** Asks before deleting a rubric; a refusal (e.g. the default rubric) stays visible. */
export function RubricDeleteDialog({
  rubric,
  onConfirm,
  onClose,
}: Readonly<RubricDeleteDialogProps>): React.ReactElement {
  const t = useTranslations("rubrics.delete");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const cancelRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    cancelRef.current?.focus();
  }, []);

  const handleConfirm = async (): Promise<void> => {
    setPending(true);
    setError(null);
    try {
      await onConfirm();
    } catch (err) {
      const detail =
        err instanceof ResourceRequestError ? err.detail : undefined;
      setError(detail ?? t("error"));
      setPending(false);
    }
  };

  return (
    <NeonModal
      open
      onClose={onClose}
      title={t("title")}
      footer={
        <div className="mt-6 flex justify-end gap-2">
          <NeonButton ref={cancelRef} variant="ghost" onClick={onClose}>
            {t("cancel")}
          </NeonButton>
          <NeonButton
            variant="danger"
            loading={pending}
            onClick={() => void handleConfirm()}
          >
            {t("confirm")}
          </NeonButton>
        </div>
      }
    >
      <p className="text-sm text-text-muted">
        {t("body", { name: rubric.name })}
      </p>
      {error && (
        <p role="alert" className="mt-3 text-sm" style={{ color: NEON_RED }}>
          {error}
        </p>
      )}
    </NeonModal>
  );
}
