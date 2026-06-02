import { forwardRef, type TextareaHTMLAttributes } from "react";
import { cn } from "@/lib/utils";
import { TEXT } from "@/constants/neon";

export type NeonTextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement>;

export const NeonTextarea = forwardRef<HTMLTextAreaElement, NeonTextareaProps>(
  ({ className, style, ...props }, ref) => (
    <textarea
      ref={ref}
      className={cn(
        "flex min-h-[80px] w-full rounded-md border px-3 py-2 text-sm transition-colors resize-y",
        "border-[var(--color-neon-input-border)] bg-[var(--color-neon-input-bg)]",
        "placeholder:text-text-dim",
        "focus-visible:outline-none focus-visible:border-neon-cyan focus-visible:ring-1 focus-visible:ring-neon-cyan",
        "disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      style={{ color: TEXT, ...style }}
      {...props}
    />
  ),
);
NeonTextarea.displayName = "NeonTextarea";
