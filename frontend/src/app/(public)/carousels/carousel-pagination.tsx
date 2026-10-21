import Link from "next/link";
import { neonButtonVariants } from "@/components/atoms/neon-button";
import { TEXT_DIM } from "@/constants/neon";

interface CarouselPaginationLabels {
  navigation: string;
  previous: string;
  next: string;
  counter: string;
}

interface CarouselPaginationProps {
  page: number;
  totalPages: number;
  previousHref: string;
  nextHref: string;
  labels: CarouselPaginationLabels;
}

/** Previous/next gallery pagination (AE-0444). */
export function CarouselPagination({
  page,
  totalPages,
  previousHref,
  nextHref,
  labels,
}: CarouselPaginationProps): React.ReactElement | null {
  if (totalPages <= 1) return null;

  return (
    <nav
      aria-label={labels.navigation}
      className="mt-12 flex flex-wrap items-center justify-center gap-3"
    >
      {page > 1 ? (
        <Link
          href={previousHref}
          className={neonButtonVariants({ variant: "secondary", size: "sm" })}
          aria-label={labels.previous}
        >
          ← {labels.previous}
        </Link>
      ) : null}
      <span className="font-mono text-xs" style={{ color: TEXT_DIM }}>
        {labels.counter}
      </span>
      {page < totalPages ? (
        <Link
          href={nextHref}
          className={neonButtonVariants({ variant: "secondary", size: "sm" })}
          aria-label={labels.next}
        >
          {labels.next} →
        </Link>
      ) : null}
    </nav>
  );
}
