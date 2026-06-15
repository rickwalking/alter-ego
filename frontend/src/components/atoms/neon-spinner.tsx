import { forwardRef, type SVGAttributes } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
import { NEON_CYAN } from "@/constants/neon";

const DEFAULT_LOADING_LABEL = "Loading";

const neonSpinnerVariants = cva("animate-spin", {
  variants: {
    size: {
      sm: "h-4 w-4",
      md: "h-6 w-6",
      lg: "h-8 w-8",
    },
  },
  defaultVariants: { size: "md" },
});

export interface NeonSpinnerProps
  extends
    SVGAttributes<SVGSVGElement>,
    VariantProps<typeof neonSpinnerVariants> {}

export const NeonSpinner = forwardRef<SVGSVGElement, NeonSpinnerProps>(
  ({ className, size, ...props }, ref) => (
    <svg
      ref={ref}
      role="status"
      aria-label={DEFAULT_LOADING_LABEL}
      className={cn(neonSpinnerVariants({ size }), className)}
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      style={{ color: NEON_CYAN }}
      {...props}
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  ),
);
NeonSpinner.displayName = "NeonSpinner";

export interface SpinnerProps extends VariantProps<typeof neonSpinnerVariants> {
  /** Optional visible label rendered next to the spinner. */
  label?: string;
  /** Extra classes applied to the wrapper element. */
  className?: string;
}

/**
 * Labeled spinner wrapper. Composes the pure {@link NeonSpinner} SVG with an
 * optional visible label and a single `role="status"` live region.
 *
 * The inner SVG is marked `aria-hidden` so the wrapper is the sole status
 * element exposed to assistive technology (avoids duplicate `status` roles).
 */
export function Spinner({
  size = "md",
  label,
  className = "",
}: SpinnerProps): React.ReactElement {
  return (
    <div
      role="status"
      aria-label={label ?? DEFAULT_LOADING_LABEL}
      className={cn("inline-flex items-center gap-2", className)}
    >
      <NeonSpinner size={size} aria-hidden="true" aria-label={undefined} />
      {label && <span className="text-sm">{label}</span>}
    </div>
  );
}
