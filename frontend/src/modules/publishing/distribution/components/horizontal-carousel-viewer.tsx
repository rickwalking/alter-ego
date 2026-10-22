"use client";

import Image from "next/image";
import { useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { ChevronLeft, ChevronRight, Download, Loader } from "lucide-react";
import {
  scrollViewportToSlide,
  slideIndexFromScroll,
} from "@/lib/slide-viewport";
import { downloadSlidesZip } from "../lib/download-slides-zip";
import type { HorizontalCarouselViewerProps } from "./types";

/**
 * Instagram-style carousel viewer. Horizontal snap-scroll on desktop
 * with visible slide counter; arrow buttons for prev/next navigation
 * and a download-all button.
 *
 * Slides whose image did not load (not rendered yet) get a placeholder instead
 * of a broken image.
 */
export function HorizontalCarouselViewer({
  slideUrls,
  alt,
}: Readonly<HorizontalCarouselViewerProps>) {
  const t = useTranslations("publish.carouselViewer");
  const [activeIndex, setActiveIndex] = useState(0);
  const [isDownloading, setIsDownloading] = useState(false);
  const [missingSlides, setMissingSlides] = useState<ReadonlySet<string>>(
    () => new Set(),
  );
  const markMissing = (url: string): void =>
    setMissingSlides((current) => new Set(current).add(url));

  const handleScroll = (event: React.UIEvent<HTMLDivElement>) => {
    const target = event.currentTarget;
    const index = slideIndexFromScroll(target);
    if (index !== activeIndex) {
      setActiveIndex(index);
    }
  };

  const scrollTo = useCallback(
    (index: number) => {
      const viewport = document.getElementById("carousel-viewport");
      if (!viewport) return;
      scrollViewportToSlide(viewport, index, slideUrls.length);
    },
    [slideUrls.length],
  );

  const goPrev = useCallback(
    () => scrollTo(activeIndex - 1),
    [activeIndex, scrollTo],
  );
  const goNext = useCallback(
    () => scrollTo(activeIndex + 1),
    [activeIndex, scrollTo],
  );

  if (slideUrls.length === 0) {
    return null;
  }

  const downloadAll = async () => {
    setIsDownloading(true);
    try {
      await downloadSlidesZip(slideUrls, alt);
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="relative">
        <div
          id="carousel-viewport"
          onScroll={handleScroll}
          className="flex snap-x snap-mandatory overflow-x-auto rounded-lg border border-[var(--color-border)]"
          style={{ scrollbarWidth: "none" }}
        >
          {slideUrls.map((url, i) => (
            <div
              key={`slide-${i + 1}`}
              className="relative aspect-[4/5] w-full flex-shrink-0 snap-center"
            >
              {missingSlides.has(url) ? (
                <div className="flex h-full w-full items-center justify-center bg-[var(--color-background)] p-4 text-center text-[var(--color-text-muted)] text-sm">
                  {t("slideNotRendered")}
                </div>
              ) : (
                <Image
                  src={url}
                  alt={t("slideAlt", { title: alt, number: i + 1 })}
                  fill
                  className="object-cover"
                  sizes="(min-width: 1024px) 50vw, 100vw"
                  unoptimized
                  priority={i === 0}
                  onError={() => markMissing(url)}
                />
              )}
              <div className="absolute top-3 right-3 rounded-full bg-background/60 px-2 py-0.5 text-foreground text-xs">
                {i + 1} / {slideUrls.length}
              </div>
            </div>
          ))}
        </div>

        {slideUrls.length > 1 && (
          <>
            <button
              type="button"
              onClick={goPrev}
              disabled={activeIndex === 0}
              aria-label={t("previousSlide")}
              className="absolute left-2 top-1/2 -translate-y-1/2 rounded-full bg-background/50 p-2 text-foreground transition-opacity hover:bg-background/70 disabled:opacity-0"
            >
              <ChevronLeft className="h-5 w-5" />
            </button>
            <button
              type="button"
              onClick={goNext}
              disabled={activeIndex === slideUrls.length - 1}
              aria-label={t("nextSlide")}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded-full bg-background/50 p-2 text-foreground transition-opacity hover:bg-background/70 disabled:opacity-0"
            >
              <ChevronRight className="h-5 w-5" />
            </button>
          </>
        )}
      </div>

      <div className="flex items-center justify-between">
        <div className="flex justify-center gap-1.5">
          {slideUrls.map((url, i) => (
            <button
              key={`dot-${i + 1}`}
              type="button"
              aria-label={t("goToSlide", { number: i + 1 })}
              onClick={() => scrollTo(i)}
              className={`h-1.5 rounded-full transition-all ${
                i === activeIndex
                  ? "w-6 bg-[var(--color-primary)]"
                  : "w-1.5 bg-[var(--color-border)]"
              }`}
            />
          ))}
        </div>

        <button
          type="button"
          onClick={() => {
            void downloadAll();
          }}
          disabled={isDownloading}
          className="inline-flex items-center gap-1.5 rounded-md border border-[var(--color-border)] px-3 py-1.5 text-sm hover:bg-[var(--color-background)] disabled:opacity-50"
        >
          {isDownloading ? (
            <Loader className="h-4 w-4 animate-spin" />
          ) : (
            <Download className="h-4 w-4" />
          )}
          {isDownloading ? t("downloadingImages") : t("downloadImages")}
        </button>
      </div>
    </div>
  );
}
