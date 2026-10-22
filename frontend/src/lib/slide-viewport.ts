export function slideIndexFromScroll(target: HTMLElement): number {
  return Math.round(target.scrollLeft / target.clientWidth);
}

export function scrollViewportToSlide(
  viewport: HTMLElement,
  index: number,
  slideCount: number,
): void {
  const clamped = Math.max(0, Math.min(index, slideCount - 1));
  viewport.scrollTo({
    left: clamped * viewport.clientWidth,
    behavior: "smooth",
  });
}
