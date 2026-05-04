"use client";

import Image from "next/image";
import { useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { ChevronLeft, ChevronRight, Download } from "lucide-react";
import JSZip from "jszip";

interface HorizontalCarouselViewerProps {
  slideUrls: string[];
  alt: string;
}

/**
 * Instagram-style carousel viewer. Horizontal snap-scroll on desktop
 * with visible slide counter; arrow buttons for prev/next navigation
 * and a download-all button.
 */
export function HorizontalCarouselViewer({
  slideUrls,
  alt,
}: HorizontalCarouselViewerProps) {
  const t = useTranslations("publish.carouselViewer");
  const [activeIndex, setActiveIndex] = useState(0);

  const handleScroll = (event: React.UIEvent<HTMLDivElement>) => {
    const target = event.currentTarget;
    const index = Math.round(target.scrollLeft / target.clientWidth);
    if (index !== activeIndex) {
      setActiveIndex(index);
    }
  };

  const scrollTo = useCallback((index: number) => {
    const viewport = document.getElementById("carousel-viewport");
    if (!viewport) return;
    const clamped = Math.max(0, Math.min(index, slideUrls.length - 1));
    viewport.scrollTo({
      left: clamped * viewport.clientWidth,
      behavior: "smooth",
    });
  }, [slideUrls.length]);

  const goPrev = useCallback(() => scrollTo(activeIndex - 1), [activeIndex, scrollTo]);
  const goNext = useCallback(() => scrollTo(activeIndex + 1), [activeIndex, scrollTo]);

  if (slideUrls.length === 0) {
    return null;
  }

  const downloadAll = async () => {
    const zip = new JSZip();
    const folder = zip.folder(alt.replace(/\s+/g, "_") || "slides");
    if (!folder) return;

    const fetches = slideUrls.map(async (url, i) => {
      try {
        const response = await fetch(url);
        const blob = await response.blob();
        folder.file(`slide_${i + 1}.jpg`, blob);
      } catch {
        // Ignore individual fetch failures
      }
    });

    await Promise.all(fetches);

    const content = await zip.generateAsync({ type: "blob" });
    const downloadUrl = window.URL.createObjectURL(content);
    const a = document.createElement("a");
    a.href = downloadUrl;
    a.download = `${alt.replace(/\s+/g, "_") || "slides"}.zip`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(downloadUrl);
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
              key={url}
              className="relative aspect-[4/5] w-full flex-shrink-0 snap-center"
            >
              <Image
                src={url}
                alt={`${alt} – slide ${i + 1}`}
                fill
                className="object-cover"
                sizes="(min-width: 1024px) 50vw, 100vw"
                unoptimized
              />
              <div className="absolute top-3 right-3 rounded-full bg-black/60 px-2 py-0.5 text-white text-xs">
                {i + 1} / {slideUrls.length}
              </div>
            </div>
          ))}
        </div>

        {/* Prev / Next arrows */}
        {slideUrls.length > 1 && (
          <>
            <button
              type="button"
              onClick={goPrev}
              disabled={activeIndex === 0}
              aria-label={t("previousSlide")}
              className="absolute left-2 top-1/2 -translate-y-1/2 rounded-full bg-black/50 p-2 text-white transition-opacity hover:bg-black/70 disabled:opacity-0"
            >
              <ChevronLeft className="h-5 w-5" />
            </button>
            <button
              type="button"
              onClick={goNext}
              disabled={activeIndex === slideUrls.length - 1}
              aria-label={t("nextSlide")}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded-full bg-black/50 p-2 text-white transition-opacity hover:bg-black/70 disabled:opacity-0"
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
              key={url}
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
          onClick={downloadAll}
          className="inline-flex items-center gap-1.5 rounded-md border border-[var(--color-border)] px-3 py-1.5 text-sm hover:bg-[var(--color-background)]"
        >
          <Download className="h-4 w-4" />
          {t("downloadImages")}
        </button>
      </div>
    </div>
  );
}
