import type { SlideGenerationStatus } from "@/constants/create";
import { SlideStatusIcon } from "./progress-icons";

export interface SlideProgressItem {
  number: number;
  status: SlideGenerationStatus;
  style?: string;
  scene?: string;
}

interface SlideProgressGridProps {
  /** Per-slide status list from `phase_progress.slides`. */
  slides: SlideProgressItem[];
}

/**
 * The per-slide image-generation checklist rendered during phase 5.
 * The backend publishes one entry per slide in `phase_progress.slides`;
 * each mutates from `pending → in_flight → done | failed` as workers
 * finish, and this grid reflects the live state.
 */
export function SlideProgressGrid({ slides }: SlideProgressGridProps) {
  if (slides.length === 0) return null;

  return (
    <ul
      className="space-y-1.5 pt-1"
      aria-label="Per-slide image generation status"
      data-testid="phase-progress-slides"
    >
      {slides.map((slide) => (
        <li
          key={slide.number}
          className="flex items-start gap-2 text-xs"
          data-testid={`phase-slide-${slide.number}`}
          data-status={slide.status}
        >
          <SlideStatusIcon status={slide.status} />
          <div className="flex-1 space-y-0.5">
            <span className="font-medium text-[var(--color-text)]">
              Slide {slide.number}
            </span>
            {slide.scene ? (
              <p className="text-[var(--color-text-muted)] italic">{slide.scene}</p>
            ) : null}
          </div>
        </li>
      ))}
    </ul>
  );
}
