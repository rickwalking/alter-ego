import Link from "next/link";
import { NeonBadge } from "@/components/atoms/neon-badge";
import { NeonCard } from "@/components/molecules/neon-card";
import {
  BG_CARD,
  BG_SURFACE,
  NEON_BORDER_SUBTLE,
  NEON_CYAN,
  TEXT,
  TEXT_DIM,
} from "@/constants/neon";
import { PublicCoverImage } from "@/modules/publishing";
import { CarouselPlaceholderIcon } from "./carousel-placeholder-icon";
import { formatPublicDate } from "@/lib/public-blog-text";
import {
  carouselLanguageTag,
  type PublicCarouselCard,
} from "@/lib/public-carousels";
import type { SupportedLocale } from "@/i18n/config";

const COVER_SIZES = "(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw";

export interface CarouselCardLabels {
  slides: string;
  open: string;
  view: string;
  coverAlt: string;
}

interface CarouselCardProps {
  card: PublicCarouselCard;
  labels: CarouselCardLabels;
  locale: SupportedLocale;
}

function CoverPlaceholder(): React.ReactElement {
  return (
    <div
      className="relative flex aspect-[4/5] items-center justify-center overflow-hidden"
      style={{
        background: `linear-gradient(135deg, ${BG_SURFACE} 0%, ${BG_CARD} 100%)`,
      }}
    >
      <div
        aria-hidden="true"
        className="absolute inset-0 opacity-50"
        style={{
          backgroundImage: `linear-gradient(${NEON_BORDER_SUBTLE} 1px, transparent 1px), linear-gradient(90deg, ${NEON_BORDER_SUBTLE} 1px, transparent 1px)`,
          backgroundSize: "32px 32px",
        }}
      />
      <CarouselPlaceholderIcon size={48} />
    </div>
  );
}

export function CarouselCard({
  card,
  labels,
  locale,
}: Readonly<CarouselCardProps>): React.ReactElement {
  const date = formatPublicDate(card.createdAt, locale);
  return (
    <Link
      href={card.href}
      aria-label={labels.open}
      className="group block h-full rounded-lg no-underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-bg-deep"
    >
      <NeonCard
        padding="sm"
        className="flex h-full flex-col overflow-hidden p-0 transition-transform duration-300 group-hover:-translate-y-1 motion-reduce:transform-none"
      >
        <div className="relative">
          {card.coverUrl ? (
            <PublicCoverImage
              src={card.coverUrl}
              alt={labels.coverAlt}
              sizes={COVER_SIZES}
              frameClassName="relative aspect-[4/5] overflow-hidden"
              overlay={
                <div
                  aria-hidden="true"
                  className="absolute inset-0 bg-gradient-to-t from-[#060a12] via-transparent to-transparent opacity-80"
                />
              }
            />
          ) : (
            <CoverPlaceholder />
          )}
          <div className="absolute left-3 top-3 flex items-center gap-2">
            <NeonBadge size="sm" variant="cyan">
              {carouselLanguageTag(card.language)}
            </NeonBadge>
          </div>
        </div>
        <div className="flex flex-1 flex-col p-4">
          <h2
            className="line-clamp-2 text-base font-bold leading-snug tracking-tight"
            style={{ color: TEXT }}
          >
            {card.title}
          </h2>
          <div
            className="mt-auto flex flex-wrap items-center gap-2 pt-4 text-xs"
            style={{ color: TEXT_DIM }}
          >
            {date ? <time dateTime={card.createdAt}>{date}</time> : null}
            {date && card.slideCount !== null ? (
              <span aria-hidden="true">·</span>
            ) : null}
            {card.slideCount !== null ? <span>{labels.slides}</span> : null}
          </div>
          <span
            className="mt-3 inline-flex items-center gap-1 text-xs font-semibold opacity-0 transition-opacity duration-200 group-hover:opacity-100 group-focus-visible:opacity-100 motion-reduce:transition-none"
            style={{ color: NEON_CYAN }}
            aria-hidden="true"
          >
            {labels.view}
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M5 12h14M13 6l6 6-6 6" />
            </svg>
          </span>
        </div>
      </NeonCard>
    </Link>
  );
}
