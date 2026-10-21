"use client";

import { useCallback, useRef, useState } from "react";
import Image from "next/image";

import { useTranslations } from "next-intl";
import { ChevronLeft, ChevronRight } from "lucide-react";

export interface SlideViewport {
  activeIndex: number;
  viewportRef: React.RefObject<HTMLDivElement | null>;
  handleScroll: (event: React.UIEvent<HTMLDivElement>) => void;
  goPrev: () => void;
  goNext: () => void;
}

export function useSlideViewport(slideUrls: string[]): SlideViewport {
  const [activeIndex, setActiveIndex] = useState(0);
  const viewportRef = useRef<HTMLDivElement>(null);

  const scrollToIndex = useCallback(
    (index: number): void => {
      const viewport = viewportRef.current;
      if (!viewport) return;
      const clamped = Math.max(0, Math.min(index, slideUrls.length - 1));
      viewport.scrollTo({
        left: clamped * viewport.clientWidth,
        behavior: "smooth",
      });
    },
    [slideUrls.length],
  );

  const handleScroll = useCallback(
    (event: React.UIEvent<HTMLDivElement>): void => {
      const target = event.currentTarget;
      const index = Math.round(target.scrollLeft / target.clientWidth);
      if (index !== activeIndex) setActiveIndex(index);
    },
    [activeIndex],
  );

  const goPrev = useCallback((): void => {
    const newIndex = Math.max(0, activeIndex - 1);
    setActiveIndex(newIndex);
    scrollToIndex(newIndex);
  }, [activeIndex, scrollToIndex]);

  const goNext = useCallback((): void => {
    const newIndex = Math.min(slideUrls.length - 1, activeIndex + 1);
    setActiveIndex(newIndex);
    scrollToIndex(newIndex);
  }, [activeIndex, slideUrls.length, scrollToIndex]);

  return { activeIndex, viewportRef, handleScroll, goPrev, goNext };
}

export function SlideNav({
  activeIndex,
  count,
  onPrev,
  onNext,
}: Readonly<{
  activeIndex: number;
  count: number;
  onPrev: () => void;
  onNext: () => void;
}>): React.ReactElement {
  const t = useTranslations("create");
  return (
    <>
      <button
        type="button"
        onClick={onPrev}
        disabled={activeIndex === 0}
        aria-label={t("preview.previousSlide")}
        className="absolute left-2 top-1/2 -translate-y-1/2 rounded-full bg-background/50 p-2 text-foreground transition-opacity hover:bg-background/70 disabled:opacity-0"
      >
        <ChevronLeft className="h-5 w-5" />
      </button>
      <button
        type="button"
        onClick={onNext}
        disabled={activeIndex === count - 1}
        aria-label={t("preview.nextSlide")}
        className="absolute right-2 top-1/2 -translate-y-1/2 rounded-full bg-background/50 p-2 text-foreground transition-opacity hover:bg-background/70 disabled:opacity-0"
      >
        <ChevronRight className="h-5 w-5" />
      </button>
    </>
  );
}

export function PreviewSlides({
  slideUrls,
  title,
}: Readonly<{
  slideUrls: string[];
  title: string;
}>): React.ReactElement {
  const { activeIndex, viewportRef, handleScroll, goPrev, goNext } =
    useSlideViewport(slideUrls);
  return (
    <div className="relative">
      <div
        ref={viewportRef}
        onScroll={handleScroll}
        className="flex snap-x snap-mandatory overflow-x-auto"
        style={{ scrollbarWidth: "none" }}
      >
        {slideUrls.map((url, i) => (
          <div
            key={`slide-${i + 1}`}
            className="relative aspect-[4/5] w-full flex-shrink-0 snap-center"
          >
            <Image
              src={url}
              alt={`${title} – slide ${i + 1}`}
              fill
              className="object-cover"
              sizes="(min-width: 1024px) 33vw, 100vw"
              unoptimized
            />
            <div className="absolute top-3 right-3 rounded-full bg-background/60 px-2 py-0.5 text-foreground text-xs">
              {i + 1} / {slideUrls.length}
            </div>
          </div>
        ))}
      </div>
      {slideUrls.length > 1 && (
        <SlideNav
          activeIndex={activeIndex}
          count={slideUrls.length}
          onPrev={goPrev}
          onNext={goNext}
        />
      )}
    </div>
  );
}
