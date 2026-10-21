import { describe, expect, it } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { PublicCoverImage } from "./public-cover-image";

// Scenario: A missing image does not render a broken image
describe("PublicCoverImage", () => {
  it("renders the image inside its frame with the overlay", () => {
    const { container } = render(
      <PublicCoverImage
        src="/api/carousels/p/images/slide_1.jpg?lang=pt"
        alt="Cover"
        sizes="100vw"
        frameClassName="frame"
        frameStyle={{ height: 100 }}
        overlay={<div data-testid="overlay" />}
      />,
    );
    const frame = container.firstElementChild as HTMLElement;
    expect(frame).toHaveClass("frame");
    expect(frame.style.height).toBe("100px");
    expect(screen.getByRole("img")).toHaveAttribute("alt", "Cover");
    expect(screen.getByTestId("overlay")).toBeInTheDocument();
  });

  it("removes the frame when the image fails to load", () => {
    const { container } = render(
      <PublicCoverImage src="/missing.jpg" alt="Cover" sizes="100vw" />,
    );
    fireEvent.error(screen.getByRole("img"));
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing without a source", () => {
    const { container } = render(
      <PublicCoverImage src="" alt="Cover" sizes="100vw" />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
