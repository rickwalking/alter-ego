import Link from "next/link";
import { forwardRef, type ComponentProps } from "react";
import { cn } from "@/lib/utils";
import { NEON_CYAN, TEXT_MUTED } from "@/constants/neon";

export interface NeonLinkProps extends ComponentProps<typeof Link> {
  muted?: boolean;
}

export const NeonLink = forwardRef<HTMLAnchorElement, NeonLinkProps>(
  ({ className, muted, style, ...props }, ref) => (
    <Link
      ref={ref}
      className={cn(
        "text-sm font-medium transition-colors duration-200 hover:opacity-90",
        className,
      )}
      style={{ color: muted ? TEXT_MUTED : NEON_CYAN, ...style }}
      {...props}
    />
  ),
);
NeonLink.displayName = "NeonLink";
