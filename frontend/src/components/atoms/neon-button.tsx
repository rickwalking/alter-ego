import {
  forwardRef,
  type ButtonHTMLAttributes,
  type ReactNode,
} from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
import { NeonSpinner } from "@/components/atoms/neon-spinner";

const neonButtonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-md font-semibold transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-bg-deep disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        primary:
          "bg-gradient-to-r from-neon-cyan to-[var(--color-neon-cyan-teal-end)] text-bg-deep shadow-[var(--shadow-neon-button)] hover:shadow-[var(--shadow-neon-button-hover)]",
        default:
          "bg-gradient-to-r from-neon-cyan to-[var(--color-neon-cyan-teal-end)] text-bg-deep shadow-[var(--shadow-neon-button)] hover:shadow-[var(--shadow-neon-button-hover)]",
        secondary:
          "border border-[color:var(--color-neon-cyan-border-30)] text-neon-cyan bg-transparent hover:bg-neon-cyan-dim",
        outline:
          "border border-[color:var(--color-neon-cyan-border-30)] text-neon-cyan bg-transparent hover:bg-neon-cyan-dim",
        ghost:
          "bg-transparent text-text-primary hover:bg-neon-cyan-dim",
        link: "bg-transparent text-neon-cyan underline-offset-4 hover:underline",
        danger:
          "bg-gradient-to-r from-neon-red to-[var(--color-neon-red-dark-end)] text-white shadow-[var(--shadow-neon-danger)]",
        destructive:
          "bg-gradient-to-r from-neon-red to-[var(--color-neon-red-dark-end)] text-white shadow-[var(--shadow-neon-danger)]",
      },
      size: {
        sm: "px-3 py-1.5 text-xs h-8",
        md: "px-4 py-2 text-sm h-10",
        default: "px-4 py-2 text-sm h-10",
        lg: "px-6 py-3 text-base h-12",
        icon: "h-10 w-10 p-0",
      },
      fullWidth: {
        true: "w-full",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  },
);

export interface NeonButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof neonButtonVariants> {
  loading?: boolean;
  icon?: ReactNode;
  iconPosition?: "left" | "right";
}

export const NeonButton = forwardRef<HTMLButtonElement, NeonButtonProps>(
  (
    {
      className,
      variant,
      size,
      fullWidth,
      loading,
      disabled,
      icon,
      iconPosition = "left",
      children,
      type = "button",
      ...props
    },
    ref,
  ) => {
    const isDisabled = disabled || loading;

    return (
      <button
        ref={ref}
        type={type}
        disabled={isDisabled}
        className={cn(neonButtonVariants({ variant, size, fullWidth, className }))}
        aria-disabled={isDisabled}
        aria-busy={loading}
        {...props}
      >
        {loading && <NeonSpinner size="sm" />}
        {!loading && icon && iconPosition === "left" && (
          <span aria-hidden="true">{icon}</span>
        )}
        {children}
        {!loading && icon && iconPosition === "right" && (
          <span aria-hidden="true">{icon}</span>
        )}
      </button>
    );
  },
);
NeonButton.displayName = "NeonButton";

export { neonButtonVariants };
