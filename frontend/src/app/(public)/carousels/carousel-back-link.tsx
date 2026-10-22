import Link from "next/link";
import { TEXT_MUTED } from "@/constants/neon";
import { BackArrowIcon } from "@/components/atoms/back-arrow-icon";

interface CarouselBackLinkProps {
  href: string;
  label: string;
}

/** Back link shared by the public carousel pages. */
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
      <BackArrowIcon />
      {label}
    </Link>
  );
}
