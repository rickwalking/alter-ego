import { forwardRef, type InputHTMLAttributes } from "react";
import { cn } from "@/lib/utils";
import { TEXT } from "@/constants/neon";

export type NeonInputProps = InputHTMLAttributes<HTMLInputElement>;

export const NeonInput = forwardRef<HTMLInputElement, NeonInputProps>(
  ({ className, style, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "flex h-10 w-full rounded-md border px-3 py-2 text-sm transition-colors",
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
NeonInput.displayName = "NeonInput";
