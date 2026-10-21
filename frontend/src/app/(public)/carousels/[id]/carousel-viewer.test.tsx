import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CarouselViewer } from "./carousel-viewer";
import type { CarouselPublicSlide } from "@/schemas/carousel";

// Feature: Public carousel viewer (AE-0444)
// frontend/tests/features/public_carousel_viewer_ae0444.feature

const SLIDES: CarouselPublicSlide[] = [
  { slide_number: 1, heading: "Abertura", image_url: "/slide-1.jpg" },
  { slide_number: 2, heading: "Contexto", image_url: "/slide-2.jpg" },
  { slide_number: 3, heading: null, image_url: "/slide-3.jpg" },
];

function renderViewer(slides: CarouselPublicSlide[] = SLIDES) {
  return render(<CarouselViewer title="IA sem hype" slides={slides} />);
}

describe("CarouselViewer (AE-0444)", () => {
  it("starts on the first slide with the previous control disabled", () => {
    renderViewer();

    expect(screen.getByText("Slide 1 of 3")).toBeInTheDocument();
    expect(screen.getByAltText("Slide 1 of 3: Abertura")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Previous slide" }),
    ).toBeDisabled();
    expect(screen.getByRole("button", { name: "Next slide" })).toBeEnabled();
  });

  it("moves with the next and previous buttons", () => {
    renderViewer();

    fireEvent.click(screen.getByRole("button", { name: "Next slide" }));
    expect(screen.getByText("Slide 2 of 3")).toBeInTheDocument();
    expect(screen.getByAltText("Slide 2 of 3: Contexto")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Previous slide" }));
    expect(screen.getByText("Slide 1 of 3")).toBeInTheDocument();
  });

  it("uses the fallback alt text when a slide has no heading", () => {
    renderViewer();

    fireEvent.click(screen.getByRole("button", { name: "Go to slide 3" }));
    expect(screen.getByAltText("Slide 3 of 3")).toBeInTheDocument();
  });

  it("supports arrow, home and end keys", () => {
    renderViewer();
    const region = screen.getByRole("region", {
      name: "Carousel viewer: IA sem hype",
    });

    fireEvent.keyDown(region, { key: "ArrowRight" });
    expect(screen.getByText("Slide 2 of 3")).toBeInTheDocument();

    fireEvent.keyDown(region, { key: "End" });
    expect(screen.getByText("Slide 3 of 3")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Next slide" })).toBeDisabled();

    fireEvent.keyDown(region, { key: "ArrowLeft" });
    expect(screen.getByText("Slide 2 of 3")).toBeInTheDocument();

    fireEvent.keyDown(region, { key: "Home" });
    expect(screen.getByText("Slide 1 of 3")).toBeInTheDocument();
  });

  it("swipes left and right but ignores short or vertical gestures", () => {
    renderViewer();
    const region = screen.getByRole("region", {
      name: "Carousel viewer: IA sem hype",
    });

    fireEvent.touchStart(region, {
      touches: [{ clientX: 200, clientY: 100 }],
    });
    fireEvent.touchEnd(region, {
      changedTouches: [{ clientX: 100, clientY: 105 }],
    });
    expect(screen.getByText("Slide 2 of 3")).toBeInTheDocument();

    fireEvent.touchStart(region, {
      touches: [{ clientX: 100, clientY: 100 }],
    });
    fireEvent.touchEnd(region, {
      changedTouches: [{ clientX: 120, clientY: 100 }],
    });
    expect(screen.getByText("Slide 2 of 3")).toBeInTheDocument();

    fireEvent.touchStart(region, {
      touches: [{ clientX: 200, clientY: 100 }],
    });
    fireEvent.touchEnd(region, {
      changedTouches: [{ clientX: 200, clientY: 220 }],
    });
    expect(screen.getByText("Slide 2 of 3")).toBeInTheDocument();

    fireEvent.touchStart(region, {
      touches: [{ clientX: 100, clientY: 100 }],
    });
    fireEvent.touchEnd(region, {
      changedTouches: [{ clientX: 200, clientY: 100 }],
    });
    expect(screen.getByText("Slide 1 of 3")).toBeInTheDocument();
  });

  it("renders a dot per slide and marks the active one", () => {
    renderViewer();

    const first = screen.getByRole("button", { name: "Go to slide 1" });
    const second = screen.getByRole("button", { name: "Go to slide 2" });

    expect(first).toHaveAttribute("aria-current", "true");
    expect(second).not.toHaveAttribute("aria-current");

    fireEvent.click(second);
    expect(second).toHaveAttribute("aria-current", "true");
    expect(first).not.toHaveAttribute("aria-current");
  });

  it("renders nothing without slides", () => {
    const { container } = renderViewer([]);

    expect(container).toBeEmptyDOMElement();
  });
});
