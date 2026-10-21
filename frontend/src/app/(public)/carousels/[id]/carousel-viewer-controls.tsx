import { NEON_CYAN } from "@/constants/neon";
import type { CarouselPublicSlide } from "@/schemas/carousel";

const INACTIVE_DOT_COLOR = "rgba(255,255,255,0.2)";

/** Directional chevron for the viewer controls (AE-0444). */
export function CarouselChevron({
  direction,
}: {
  direction: "left" | "right";
}): React.ReactElement {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {direction === "left" ? (
        <path d="m15 18-6-6 6-6" />
      ) : (
        <path d="m9 18 6-6-6-6" />
      )}
    </svg>
  );
}

interface CarouselSlideDotsProps {
  slides: CarouselPublicSlide[];
  activeIndex: number;
  onSelect: (index: number) => void;
  labelFor: (slideNumber: number) => string;
}

/** Slide dots with the active indicator (AE-0444). */
export function CarouselSlideDots({
  slides,
  activeIndex,
  onSelect,
  labelFor,
}: CarouselSlideDotsProps): React.ReactElement {
  return (
    <div className="mt-4 flex flex-wrap justify-center gap-1">
      {slides.map((slide, slideIndex) => {
        const active = slideIndex === activeIndex;
        return (
          <button
            key={`${slide.slide_number}-${slide.image_url}`}
            type="button"
            onClick={() => onSelect(slideIndex)}
            aria-label={labelFor(slide.slide_number)}
            aria-current={active ? "true" : undefined}
            className="flex h-8 w-8 items-center justify-center rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neon-cyan"
          >
            <span
              aria-hidden="true"
              className="h-2.5 rounded-full transition-all duration-200 motion-reduce:transition-none"
              style={{
                width: active ? "20px" : "10px",
                background: active ? NEON_CYAN : INACTIVE_DOT_COLOR,
                boxShadow: active ? `0 0 10px ${NEON_CYAN}` : undefined,
              }}
            />
          </button>
        );
      })}
    </div>
  );
}
