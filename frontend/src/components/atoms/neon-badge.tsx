import { forwardRef, type HTMLAttributes } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
import {
  BADGE_COLORS,
  type NeonBadgeVariant,
} from "@/schemas/neon-badge";

const neonBadgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full font-semibold transition-colors",
  {
    variants: {
      size: {
        sm: "px-2 py-0.5 text-[10px]",
        md: "px-2.5 py-0.5 text-xs",
      },
      outline: {
        true: "border bg-transparent",
        false: "border-transparent",
      },
    },
    defaultVariants: { size: "md", outline: false },
  },
);

type LegacyBadgeVariant =
  | "default"
  | "secondary"
  | "destructive"
  | "outline";

const LEGACY_BADGE_MAP: Record<LegacyBadgeVariant, NeonBadgeVariant> = {
  default: "cyan",
  secondary: "teal",
  destructive: "red",
  outline: "cyan",
};

export interface NeonBadgeProps
  extends HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof neonBadgeVariants> {
  variant?: NeonBadgeVariant | LegacyBadgeVariant;
  dot?: boolean;
}

export const NeonBadge = forwardRef<HTMLSpanElement, NeonBadgeProps>(
  (
    {
      className,
      variant = "cyan",
      size,
      dot,
      outline,
      style,
      children,
      ...props
    },
    ref,
  ) => {
    const resolvedVariant: NeonBadgeVariant =
      variant in LEGACY_BADGE_MAP
        ? LEGACY_BADGE_MAP[variant as LegacyBadgeVariant]
        : (variant as NeonBadgeVariant);
    const isOutline = outline ?? variant === "outline";
    const colors = BADGE_COLORS[resolvedVariant];

    return (
      <span
        ref={ref}
        className={cn(neonBadgeVariants({ size, outline: isOutline }), className)}
        style={{
          background: isOutline ? "transparent" : colors.bg,
          color: colors.text,
          borderColor: isOutline ? colors.text : undefined,
          ...style,
        }}
        {...props}
      >
        {dot && (
          <span
            className="h-1.5 w-1.5 rounded-full shrink-0"
            style={{ background: colors.text }}
            aria-hidden="true"
          />
        )}
        {children}
      </span>
    );
  },
);
NeonBadge.displayName = "NeonBadge";
