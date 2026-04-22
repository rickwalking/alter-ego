"use client";

import { useState } from "react";

interface HorizontalCarouselViewerProps {
  slideUrls: string[];
  alt: string;
}

/**
 * Instagram-style carousel viewer. Horizontal snap-scroll on desktop
 * with visible slide counter; dots under the viewport let the user
 * jump to a specific slide.
 */
export function HorizontalCarouselViewer({
  slideUrls,
  alt,
}: HorizontalCarouselViewerProps) {
  const [activeIndex, setActiveIndex] = useState(0);

  if (slideUrls.length === 0) {
    return null;
  }

  const handleScroll = (event: React.UIEvent<HTMLDivElement>) => {
    const target = event.currentTarget;
    const index = Math.round(target.scrollLeft / target.clientWidth);
    if (index !== activeIndex) {
      setActiveIndex(index);
    }
  };

  const scrollTo = (index: number) => {
    const viewport = document.getElementById("carousel-viewport");
    if (!viewport) return;
    viewport.scrollTo({
      left: index * viewport.clientWidth,
      behavior: "smooth",
    });
  };

  return (
    <div className="space-y-3">
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
            <img
              src={url}
              alt={`${alt} – slide ${i + 1}`}
              className="h-full w-full object-cover"
            />
            <div className="absolute top-3 right-3 rounded-full bg-black/60 px-2 py-0.5 text-white text-xs">
              {i + 1} / {slideUrls.length}
            </div>
          </div>
        ))}
      </div>
      <div className="flex justify-center gap-1.5">
        {slideUrls.map((url, i) => (
          <button
            key={url}
            type="button"
            aria-label={`Go to slide ${i + 1}`}
            onClick={() => scrollTo(i)}
            className={`h-1.5 rounded-full transition-all ${
              i === activeIndex
                ? "w-6 bg-[var(--color-primary)]"
                : "w-1.5 bg-[var(--color-border)]"
            }`}
          />
        ))}
      </div>
    </div>
  );
}
