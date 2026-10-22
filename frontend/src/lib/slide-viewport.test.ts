import { describe, expect, it, vi } from "vitest";
import { scrollViewportToSlide, slideIndexFromScroll } from "./slide-viewport";

function viewportStub(scrollLeft: number, clientWidth: number) {
  const scrollTo = vi.fn();
  return {
    element: { scrollLeft, clientWidth, scrollTo } as unknown as HTMLElement,
    scrollTo,
  };
}

describe("slide-viewport", () => {
  it("rounds the scroll offset to the nearest slide index", () => {
    // Scenario: scroll offset maps to a slide index
    expect(slideIndexFromScroll(viewportStub(260, 100).element)).toBe(3);
    expect(slideIndexFromScroll(viewportStub(240, 100).element)).toBe(2);
  });

  it("scrolls smoothly to the requested slide", () => {
    // Scenario: scrolling to a slide
    const { element, scrollTo } = viewportStub(0, 200);
    scrollViewportToSlide(element, 2, 5);
    expect(scrollTo).toHaveBeenCalledWith({ left: 400, behavior: "smooth" });
  });

  it("clamps the target index to the slide range", () => {
    // Scenario: out-of-range indexes are clamped
    const low = viewportStub(0, 100);
    scrollViewportToSlide(low.element, -3, 4);
    expect(low.scrollTo).toHaveBeenCalledWith({ left: 0, behavior: "smooth" });
    const high = viewportStub(0, 100);
    scrollViewportToSlide(high.element, 9, 4);
    expect(high.scrollTo).toHaveBeenCalledWith({
      left: 300,
      behavior: "smooth",
    });
  });
});
