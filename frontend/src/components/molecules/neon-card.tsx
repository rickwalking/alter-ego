import {
  forwardRef,
  type HTMLAttributes,
  type KeyboardEvent,
  type MouseEventHandler,
} from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
import {
  CARD_ACCENT_COLORS,
  CARD_PADDING_MAP,
  type NeonCardAccent,
} from "@/schemas/neon-card";
import { TEXT_MUTED } from "@/constants/neon";

const neonCardVariants = cva(
  "rounded-lg border border-[var(--color-neon-card-border)] bg-bg-card text-text-primary shadow-sm transition-all duration-200",
  {
    variants: {
      hover: {
        true: "cursor-pointer hover:border-[var(--color-neon-card-hover-border)] hover:-translate-y-0.5 hover:shadow-[var(--shadow-neon-card-hover)]",
        false: "",
      },
      padding: {
        sm: CARD_PADDING_MAP.sm,
        md: CARD_PADDING_MAP.md,
        lg: CARD_PADDING_MAP.lg,
      },
    },
    defaultVariants: { hover: false, padding: "md" },
  },
);

export interface NeonCardProps
  extends HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof neonCardVariants> {
  accent?: NeonCardAccent;
  title?: string;
  subtitle?: string;
  onClick?: MouseEventHandler<HTMLDivElement>;
}

export const NeonCard = forwardRef<HTMLDivElement, NeonCardProps>(
  (
    {
      className,
      accent = "none",
      hover,
      padding,
      title,
      subtitle,
      onClick,
      children,
      style,
      ...props
    },
    ref,
  ) => {
    const accentColor =
      accent !== "none" ? CARD_ACCENT_COLORS[accent] : undefined;

    return (
      <div
        ref={ref}
        role={onClick ? "button" : undefined}
        tabIndex={onClick ? 0 : undefined}
        onClick={onClick}
        onKeyDown={
          onClick
            ? (e: KeyboardEvent<HTMLDivElement>) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onClick(
                    e as unknown as Parameters<MouseEventHandler<HTMLDivElement>>[0],
                  );
                }
              }
            : undefined
        }
        className={cn(neonCardVariants({ hover: hover ?? !!onClick, padding, className }))}
        style={{
          borderTopWidth: accentColor ? "2px" : undefined,
          borderTopColor: accentColor,
          ...style,
        }}
        {...props}
      >
        {title && (
          <div className="mb-4">
            <h3 className="text-lg font-bold tracking-tight">{title}</h3>
            {subtitle && (
              <p className="text-sm mt-1" style={{ color: TEXT_MUTED }}>
                {subtitle}
              </p>
            )}
          </div>
        )}
        {children}
      </div>
    );
  },
);
NeonCard.displayName = "NeonCard";

export const NeonCardHeader = forwardRef<
  HTMLDivElement,
  HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex flex-col space-y-1.5 pb-4", className)}
    {...props}
  />
));
NeonCardHeader.displayName = "NeonCardHeader";

export const NeonCardTitle = forwardRef<
  HTMLParagraphElement,
  HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn("text-lg font-bold leading-none tracking-tight", className)}
    {...props}
  />
));
NeonCardTitle.displayName = "NeonCardTitle";

export const NeonCardDescription = forwardRef<
  HTMLParagraphElement,
  HTMLAttributes<HTMLParagraphElement>
>(({ className, style, ...props }, ref) => (
  <p
    ref={ref}
    className={cn("text-sm", className)}
    style={{ color: TEXT_MUTED, ...style }}
    {...props}
  />
));
NeonCardDescription.displayName = "NeonCardDescription";

export const NeonCardContent = forwardRef<
  HTMLDivElement,
  HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("pt-0", className)} {...props} />
));
NeonCardContent.displayName = "NeonCardContent";

export const NeonCardFooter = forwardRef<
  HTMLDivElement,
  HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex items-center pt-4", className)}
    {...props}
  />
));
NeonCardFooter.displayName = "NeonCardFooter";
