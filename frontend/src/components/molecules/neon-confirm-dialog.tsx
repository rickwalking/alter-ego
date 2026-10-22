"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonModal } from "@/components/molecules/neon-modal";
import { NEON_RED } from "@/constants/neon";
import {
  ResourceRequestError,
  requestErrorText,
} from "@/lib/use-resource-collection";

export interface NeonConfirmDialogProps {
  title: string;
  body: ReactNode;
  confirmLabel: string;
  cancelLabel: string;
  /** Shown when the action fails without a message of its own. */
  errorFallback: string;
  /** Messages for specific HTTP statuses of a failed action (e.g. 409 in use). */
  statusMessages?: Readonly<Record<number, string>>;
  onConfirm: () => Promise<void>;
  onClose: () => void;
}

/**
 * Asks before a destructive action. Cancel takes focus first; a refusal
 * (the API's own sentence, or ``errorFallback``) stays visible in the dialog.
 */
export function NeonConfirmDialog({
  title,
  body,
  confirmLabel,
  cancelLabel,
  errorFallback,
  statusMessages,
  onConfirm,
  onClose,
}: Readonly<NeonConfirmDialogProps>): React.ReactElement {
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
      const byStatus =
        err instanceof ResourceRequestError
          ? statusMessages?.[err.status]
          : undefined;
      setError(byStatus ?? requestErrorText(err, errorFallback));
      setPending(false);
    }
  };

  return (
    <NeonModal
      open
      onClose={onClose}
      title={title}
      footer={
        <div className="mt-6 flex justify-end gap-2">
          <NeonButton ref={cancelRef} variant="ghost" onClick={onClose}>
            {cancelLabel}
          </NeonButton>
          <NeonButton
            variant="danger"
            loading={pending}
            onClick={() => void handleConfirm()}
          >
            {confirmLabel}
          </NeonButton>
        </div>
      }
    >
      <p className="text-sm text-text-muted">{body}</p>
      {error && (
        <p role="alert" className="mt-3 text-sm" style={{ color: NEON_RED }}>
          {error}
        </p>
      )}
    </NeonModal>
  );
}
