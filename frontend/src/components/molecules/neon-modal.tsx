"use client";

import { type ReactNode, useEffect, useRef } from "react";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonCard } from "@/components/molecules/neon-card";
import { useFocusTrap } from "@/lib/use-focus-trap";

export interface NeonModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  children: ReactNode;
  footer?: ReactNode;
}

/**
 * Modal dialog: Escape or the backdrop closes it; keyboard focus moves into the
 * card on open, Tab / Shift+Tab stay inside it, and focus returns to the
 * element that opened it on close.
 */
export function NeonModal({
  open,
  onClose,
  title,
  children,
  footer,
}: Readonly<NeonModalProps>): React.ReactElement | null {
  const cardRef = useRef<HTMLDivElement>(null);
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
      role="dialog"
      aria-modal="true"
      aria-labelledby={title ? "neon-modal-title" : undefined}
    >
      <button
        type="button"
        className="absolute inset-0 cursor-default"
        aria-label="Close modal"
        onClick={onClose}
      />
      <NeonCard
        ref={cardRef}
        padding="lg"
        className="relative z-10 max-w-lg w-full"
      >
        {title && (
          <h2 id="neon-modal-title" className="text-lg font-bold mb-4">
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
