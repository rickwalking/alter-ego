import { forwardRef, type LabelHTMLAttributes } from "react";
import { cn } from "@/lib/utils";
import { TEXT_MUTED } from "@/constants/neon";

export interface NeonLabelProps extends LabelHTMLAttributes<HTMLLabelElement> {
  required?: boolean;
}

export const NeonLabel = forwardRef<HTMLLabelElement, NeonLabelProps>(
  ({ className, children, required, ...props }, ref) => (
    <label
      ref={ref}
      className={cn("text-sm font-medium", className)}
      style={{ color: TEXT_MUTED }}
      {...props}
    >
      {children}
      {required && (
        <span className="text-neon-red ml-0.5" aria-hidden="true">
          *
        </span>
      )}
    </label>
  ),
);
NeonLabel.displayName = "NeonLabel";
