import Link from "next/link";
import { TEXT_MUTED } from "@/constants/neon";

interface CarouselBackLinkProps {
  href: string;
  label: string;
}

/** Back link shared by the public carousel pages (AE-0444). */
export function CarouselBackLink({
  href,
  label,
}: Readonly<CarouselBackLinkProps>): React.ReactElement {
  return (
    <Link
      href={href}
      className="mb-8 inline-flex items-center gap-2 text-sm no-underline transition-opacity hover:opacity-80"
      style={{ color: TEXT_MUTED }}
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="m12 19-7-7 7-7" />
        <path d="M19 12H5" />
      </svg>
      {label}
    </Link>
  );
}
