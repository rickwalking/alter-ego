"use client";

import { type ReactNode, useEffect, useId, useRef } from "react";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonCard } from "@/components/molecules/neon-card";
import { useFocusTrap } from "@/lib/use-focus-trap";

export interface NeonModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  /** Replaces the default Close row; pass `false` for no footer at all. */
  footer?: ReactNode;
  /** `alertdialog` for a dialog that asks to confirm a destructive action. */
  role?: "dialog" | "alertdialog";
  /** Accessible name of the backdrop button (translated by the caller). */
  closeLabel?: string;
}

const DEFAULT_CLOSE_LABEL = "Close modal";

/**
 * Modal dialog: Escape or the backdrop closes it; keyboard focus moves into the
 * card on open, Tab / Shift+Tab stay inside it, and focus returns to the
 * element that opened it on close. The card scrolls inside the viewport, so a
 * tall dialog still fits a phone screen.
 */
export function NeonModal({
  open,
  onClose,
  title,
  children,
  footer,
  role = "dialog",
  closeLabel = DEFAULT_CLOSE_LABEL,
}: Readonly<NeonModalProps>): React.ReactElement | null {
  const cardRef = useRef<HTMLDivElement>(null);
  const titleId = useId();
  useFocusTrap(cardRef, open);
  useEffect(() => {
    if (!open) {
      return;
    }
    const handleEscape = (e: KeyboardEvent): void => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [open, onClose]);

  if (!open) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "rgba(6,10,18,0.85)" }}
      role={role}
      aria-modal="true"
      aria-labelledby={title ? titleId : undefined}
    >
      <button
        type="button"
        className="absolute inset-0 cursor-default"
        aria-label={closeLabel}
        onClick={onClose}
      />
      <NeonCard
        ref={cardRef}
        padding="lg"
        className="relative z-10 max-h-[calc(100dvh-2rem)] w-full max-w-lg overflow-y-auto"
      >
        {title && (
          <h2 id={titleId} className="text-lg font-bold mb-4">
            {title}
          </h2>
        )}
        {children}
        {footer ?? (
          <div className="mt-6 flex justify-end gap-2">
            <NeonButton variant="ghost" onClick={onClose}>
              Close
            </NeonButton>
          </div>
        )}
      </NeonCard>
    </div>
  );
}
