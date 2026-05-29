import { forwardRef, type SelectHTMLAttributes } from "react";
import { cn } from "@/lib/utils";
import { TEXT } from "@/constants/neon";

export type NeonSelectProps = SelectHTMLAttributes<HTMLSelectElement>;

export const NeonSelect = forwardRef<HTMLSelectElement, NeonSelectProps>(
  ({ className, style, children, ...props }, ref) => (
    <select
      ref={ref}
      className={cn(
        "flex h-10 w-full rounded-md border px-3 py-2 text-sm transition-colors",
        "border-[var(--color-neon-input-border)] bg-[var(--color-neon-input-bg)]",
        "focus-visible:outline-none focus-visible:border-neon-cyan focus-visible:ring-1 focus-visible:ring-neon-cyan",
        "disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      style={{ color: TEXT, ...style }}
      {...props}
    >
      {children}
    </select>
  ),
);
NeonSelect.displayName = "NeonSelect";
