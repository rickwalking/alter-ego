import { NEON_CYAN } from "@/constants/neon";

interface CarouselPlaceholderIconProps {
  size: number;
  className?: string;
}

/** Decorative carousel glyph shared by cards and the empty state (AE-0444). */
export function CarouselPlaceholderIcon({
  size,
  className,
}: Readonly<CarouselPlaceholderIconProps>): React.ReactElement {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={NEON_CYAN}
      strokeWidth="1.2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <path d="M7 3v18M17 3v18" />
      <path d="m11 9 4 3-4 3z" />
    </svg>
  );
}
