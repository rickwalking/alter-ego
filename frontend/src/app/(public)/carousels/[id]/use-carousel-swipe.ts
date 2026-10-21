import { useRef, type TouchEvent } from "react";
import { CAROUSEL_SWIPE_THRESHOLD_PX } from "@/constants/carousels";

interface CarouselSwipeOptions {
  onPrevious: () => void;
  onNext: () => void;
}

interface CarouselSwipeHandlers {
  handleTouchStart: (event: TouchEvent<HTMLDivElement>) => void;
  handleTouchEnd: (event: TouchEvent<HTMLDivElement>) => void;
}

/** Horizontal swipe gestures for the public carousel viewer. */
export function useCarouselSwipe({
  onPrevious,
  onNext,
}: CarouselSwipeOptions): CarouselSwipeHandlers {
  const touchStartRef = useRef<{ x: number; y: number } | null>(null);

  const handleTouchStart = (event: TouchEvent<HTMLDivElement>): void => {
    const touch = event.touches[0];
    if (touch === undefined) return;
    touchStartRef.current = { x: touch.clientX, y: touch.clientY };
  };

  const handleTouchEnd = (event: TouchEvent<HTMLDivElement>): void => {
    const start = touchStartRef.current;
    touchStartRef.current = null;
    const touch = event.changedTouches[0];
    if (!start || touch === undefined) return;

    const deltaX = touch.clientX - start.x;
    const deltaY = touch.clientY - start.y;
    if (
      Math.abs(deltaX) < CAROUSEL_SWIPE_THRESHOLD_PX ||
      Math.abs(deltaX) <= Math.abs(deltaY)
    ) {
      return;
    }
    if (deltaX < 0) {
      onNext();
      return;
    }
    onPrevious();
  };

  return { handleTouchStart, handleTouchEnd };
}
