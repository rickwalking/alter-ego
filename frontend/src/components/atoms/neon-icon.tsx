import { forwardRef, type SVGAttributes } from "react";
import { cn } from "@/lib/utils";

export interface NeonIconProps extends SVGAttributes<SVGSVGElement> {
  path: string;
  size?: number;
}

export const NeonIcon = forwardRef<SVGSVGElement, NeonIconProps>(
  ({ path, size = 18, className, ...props }, ref) => {
    const segments = path.split("M").filter(Boolean);

    return (
      <svg
        ref={ref}
        width={size}
        height={size}
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        viewBox="0 0 24 24"
        className={cn("shrink-0", className)}
        aria-hidden="true"
        {...props}
      >
        {segments.map((seg, i) => (
          <path key={i} d={`M${seg}`} />
        ))}
      </svg>
    );
  },
);
NeonIcon.displayName = "NeonIcon";
