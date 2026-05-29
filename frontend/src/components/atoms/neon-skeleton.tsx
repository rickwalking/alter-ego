import { forwardRef, type HTMLAttributes } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const neonSkeletonVariants = cva("animate-pulse rounded-md bg-bg-elevated", {
  variants: {
    variant: {
      text: "h-4 w-full",
      circular: "rounded-full",
      rectangular: "w-full",
    },
  },
  defaultVariants: { variant: "text" },
});

export interface NeonSkeletonProps
  extends HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof neonSkeletonVariants> {
  width?: string | number;
  height?: string | number;
  count?: number;
}

export const NeonSkeleton = forwardRef<HTMLDivElement, NeonSkeletonProps>(
  ({ className, variant, width, height, count = 1, style, ...props }, ref) => {
    const items = Array.from({ length: count }, (_, i) => (
      <div
        key={i}
        ref={i === 0 ? ref : undefined}
        className={cn(neonSkeletonVariants({ variant }), className)}
        style={{
          width,
          height: height ?? (variant === "rectangular" ? 120 : undefined),
          ...style,
        }}
        aria-hidden="true"
        {...props}
      />
    ));

    if (count === 1) {
      return items[0];
    }

    return <div className="space-y-2">{items}</div>;
  },
);
NeonSkeleton.displayName = "NeonSkeleton";
