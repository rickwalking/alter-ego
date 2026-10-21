"use client";

import { useCallback, useState, type KeyboardEvent } from "react";
import Image from "next/image";
import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { CAROUSEL_SLIDE_ASPECT_CLASS } from "@/constants/carousels";
import {
  BG_SIDEBAR,
  NEON_CYAN_DIM,
  TEXT_DIM,
  TEXT_MUTED,
} from "@/constants/neon";
import type { CarouselPublicSlide } from "@/schemas/carousel";
import { CarouselChevron, CarouselSlideDots } from "./carousel-viewer-controls";
import { useCarouselSwipe } from "./use-carousel-swipe";

const SLIDE_IMAGE_SIZES = "(max-width: 768px) 100vw, 640px";

interface CarouselViewerProps {
  title: string;
  slides: CarouselPublicSlide[];
}

export function CarouselViewer({
  title,
  slides,
}: CarouselViewerProps): React.ReactElement | null {
  const t = useTranslations("carousels");
  const [index, setIndex] = useState(0);
  const total = slides.length;
  const safeIndex = Math.min(index, Math.max(total - 1, 0));
  const current = slides[safeIndex];

  const goTo = useCallback(
    (nextIndex: number) => {
      if (total === 0) return;
      setIndex(Math.max(0, Math.min(total - 1, nextIndex)));
    },
    [total],
  );

  const previous = useCallback(() => {
    goTo(safeIndex - 1);
  }, [goTo, safeIndex]);

  const next = useCallback(() => {
    goTo(safeIndex + 1);
  }, [goTo, safeIndex]);

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>): void => {
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      previous();
      return;
    }
    if (event.key === "ArrowRight") {
      event.preventDefault();
      next();
      return;
    }
    if (event.key === "Home") {
      event.preventDefault();
      goTo(0);
      return;
    }
    if (event.key === "End") {
      event.preventDefault();
      goTo(total - 1);
    }
  };

  const { handleTouchStart, handleTouchEnd } = useCarouselSwipe({
    onPrevious: previous,
    onNext: next,
  });

  if (current === undefined) {
    return null;
  }

  const alt = current.heading
    ? t("slideAlt", {
        number: current.slide_number,
        total,
        heading: current.heading,
      })
    : t("slideAltFallback", { number: current.slide_number, total });

  return (
    <div className="mx-auto mt-10 w-full max-w-3xl">
      <div
        role="region"
        aria-label={t("viewerRegion", { title })}
        tabIndex={0}
        onKeyDown={handleKeyDown}
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
        className="relative rounded-2xl border p-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-bg-deep"
        style={{
          borderColor: NEON_CYAN_DIM,
          background: BG_SIDEBAR,
          boxShadow: `0 0 70px ${NEON_CYAN_DIM}`,
          touchAction: "pan-y",
        }}
      >
        <div
          className={`relative ${CAROUSEL_SLIDE_ASPECT_CLASS} overflow-hidden rounded-xl`}
          style={{ background: "#04070d" }}
        >
          <Image
            key={current.image_url}
            src={current.image_url}
            alt={alt}
            fill
            sizes={SLIDE_IMAGE_SIZES}
            className="animate-fade-in object-contain motion-reduce:animate-none"
            unoptimized
            priority={safeIndex === 0}
          />
        </div>

        <NeonButton
          variant="secondary"
          size="icon"
          onClick={previous}
          disabled={safeIndex === 0}
          aria-label={t("previousSlide")}
          icon={<CarouselChevron direction="left" />}
          className="absolute left-4 top-1/2 -translate-y-1/2 backdrop-blur"
        />
        <NeonButton
          variant="secondary"
          size="icon"
          onClick={next}
          disabled={safeIndex === total - 1}
          aria-label={t("nextSlide")}
          icon={<CarouselChevron direction="right" />}
          className="absolute right-4 top-1/2 -translate-y-1/2 backdrop-blur"
        />
      </div>

      <div className="mt-4 flex items-center justify-between gap-4">
        <p
          aria-live="polite"
          aria-atomic="true"
          className="font-mono text-xs uppercase tracking-[0.2em]"
          style={{ color: TEXT_MUTED }}
        >
          {t("slideCounter", { current: safeIndex + 1, total })}
        </p>
        <p className="hidden text-xs sm:block" style={{ color: TEXT_DIM }}>
          {t("swipeHint")}
        </p>
      </div>

      <CarouselSlideDots
        slides={slides}
        activeIndex={safeIndex}
        onSelect={goTo}
        labelFor={(number) => t("goToSlide", { number })}
      />
    </div>
  );
}
