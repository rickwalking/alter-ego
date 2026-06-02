"use client";

import { useEffect, useState } from "react";
import { NeonBadge } from "@/components/atoms/neon-badge";
import { NeonIcon } from "@/components/atoms/neon-icon";
import type { NeonBadgeVariant } from "@/schemas/neon-badge";

const CHECK_PATH = "M20 6L9 17l-5-5";
const X_PATH = "M18 6L6 18M6 6l12 12";

export type NeonToastVariant = "success" | "error" | "info";

const TOAST_BADGE_VARIANT: Record<NeonToastVariant, NeonBadgeVariant> = {
  success: "green",
  error: "red",
  info: "cyan",
};

export interface NeonToastProps {
  message: string;
  variant?: NeonToastVariant;
  duration?: number;
  onDismiss?: () => void;
}

export function NeonToast({
  message,
  variant = "info",
  duration = 4000,
  onDismiss,
}: NeonToastProps): React.ReactElement | null {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setVisible(false);
      onDismiss?.();
    }, duration);
    return () => clearTimeout(timer);
  }, [duration, onDismiss]);

  if (!visible) {
    return null;
  }

  const iconPath = variant === "error" ? X_PATH : CHECK_PATH;

  return (
    <div
      role="status"
      className="fixed bottom-6 right-6 z-50 flex items-center gap-3 rounded-lg border border-[var(--color-neon-card-border)] bg-bg-card px-4 py-3 shadow-lg animate-slide-up"
    >
      <NeonBadge variant={TOAST_BADGE_VARIANT[variant]} dot>
        <NeonIcon path={iconPath} size={14} />
        {message}
      </NeonBadge>
      <button
        type="button"
        className="text-text-dim hover:text-text-primary text-xs"
        onClick={() => {
          setVisible(false);
          onDismiss?.();
        }}
        aria-label="Dismiss"
      >
        ×
      </button>
    </div>
  );
}
