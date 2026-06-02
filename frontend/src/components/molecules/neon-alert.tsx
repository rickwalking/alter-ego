import { forwardRef, type HTMLAttributes } from "react";
import { cn } from "@/lib/utils";
import {
  NEON_BORDER_FOCUS,
  NEON_CYAN_DIM,
  NEON_RED_BORDER,
  NEON_RED_DIM_BG,
  TEXT,
} from "@/constants/neon";

export interface NeonAlertProps extends HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "destructive";
}

export const NeonAlert = forwardRef<HTMLDivElement, NeonAlertProps>(
  ({ className, variant = "default", style, ...props }, ref) => (
    <div
      ref={ref}
      role="alert"
      className={cn("rounded-md border p-4 text-sm", className)}
      style={{
        background: variant === "destructive" ? NEON_RED_DIM_BG : NEON_CYAN_DIM,
        borderColor:
          variant === "destructive" ? NEON_RED_BORDER : NEON_BORDER_FOCUS,
        color: TEXT,
        ...style,
      }}
      {...props}
    />
  ),
);
NeonAlert.displayName = "NeonAlert";

export const NeonAlertTitle = forwardRef<
  HTMLParagraphElement,
  HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h5
    ref={ref}
    className={cn("mb-1 font-semibold leading-none tracking-tight", className)}
    {...props}
  />
));
NeonAlertTitle.displayName = "NeonAlertTitle";

export const NeonAlertDescription = forwardRef<
  HTMLParagraphElement,
  HTMLAttributes<HTMLParagraphElement>
>(({ className, style, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("text-sm opacity-90", className)}
    style={{ color: TEXT, ...style }}
    {...props}
  />
));
NeonAlertDescription.displayName = "NeonAlertDescription";
