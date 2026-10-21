import Link from "next/link";
import {
  NEON_BORDER_MEDIUM,
  NEON_CYAN,
  TEXT,
  TEXT_DIM,
} from "@/constants/neon";
import type { PublicCarouselNeighbor } from "@/lib/public-carousels";

interface CarouselNeighborsProps {
  previous: PublicCarouselNeighbor | null;
  next: PublicCarouselNeighbor | null;
  previousLabel: string;
  nextLabel: string;
  listLabel: string;
  listHref: string;
}

function NeighborLink({
  neighbor,
  label,
  direction,
}: Readonly<{
  neighbor: PublicCarouselNeighbor;
  label: string;
  direction: "left" | "right";
}>): React.ReactElement {
  const align =
    direction === "left" ? "items-start text-left" : "items-end text-right";
  return (
    <Link
      href={neighbor.href}
      aria-label={`${label}: ${neighbor.title}`}
      className={`flex max-w-full flex-col sm:max-w-[46%] gap-1 rounded-lg border p-4 no-underline transition-colors hover:border-neon-cyan focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neon-cyan ${align}`}
      style={{ borderColor: NEON_BORDER_MEDIUM }}
    >
      <span
        className="font-mono text-[10px] uppercase tracking-[0.2em]"
        style={{ color: NEON_CYAN }}
      >
        {label}
      </span>
      <span
        className="line-clamp-2 text-sm font-semibold"
        style={{ color: TEXT }}
      >
        {neighbor.title}
      </span>
    </Link>
  );
}

export function CarouselNeighbors({
  previous,
  next,
  previousLabel,
  nextLabel,
  listLabel,
  listHref,
}: Readonly<CarouselNeighborsProps>): React.ReactElement {
  return (
    <nav
      aria-label={listLabel}
      className="mx-auto mt-14 flex w-full max-w-3xl flex-col gap-4 border-t pt-8 sm:flex-row sm:items-center sm:justify-between"
      style={{ borderColor: NEON_BORDER_MEDIUM }}
    >
      <div className="flex flex-1 justify-start">
        {previous ? (
          <NeighborLink
            neighbor={previous}
            label={previousLabel}
            direction="left"
          />
        ) : null}
      </div>
      <Link
        href={listHref}
        className="text-center font-mono text-xs uppercase tracking-[0.2em] no-underline transition-opacity hover:opacity-80"
        style={{ color: TEXT_DIM }}
      >
        {listLabel}
      </Link>
      <div className="flex flex-1 justify-end">
        {next ? (
          <NeighborLink neighbor={next} label={nextLabel} direction="right" />
        ) : null}
      </div>
    </nav>
  );
}
