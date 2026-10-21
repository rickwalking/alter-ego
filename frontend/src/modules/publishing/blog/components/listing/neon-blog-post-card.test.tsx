import { describe, expect, it } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { NeonBlogPostCard } from "./neon-blog-post-card";

/** Gherkin: tests/features/public-blog-polish-ae0412.feature. */
const BASE_PROPS = {
  id: "post-1",
  title: "A post",
  subtitle: "A subtitle",
  niche: "AI models",
  imageUrl: "/api/carousels/p/images/slide_1.jpg?lang=pt",
  createdAt: "2026-10-14T12:00:00Z",
  href: "/blog/post-1",
};

describe("NeonBlogPostCard", () => {
  // Scenario: Dates follow the visitor's language
  it("formats the date for Portuguese visitors", () => {
    render(<NeonBlogPostCard {...BASE_PROPS} locale="pt" />);
    expect(screen.getByText("14/10/2026")).toBeInTheDocument();
  });

  it("formats the date for English visitors", () => {
    render(<NeonBlogPostCard {...BASE_PROPS} locale="en" />);
    expect(screen.getByText("Oct 14, 2026")).toBeInTheDocument();
  });

  it("defaults to the default (English) locale", () => {
    render(<NeonBlogPostCard {...BASE_PROPS} />);
    expect(screen.getByText("Oct 14, 2026")).toBeInTheDocument();
  });

  // Scenario: Invalid dates are not printed
  it("omits the date when it is missing", () => {
    const { container } = render(
      <NeonBlogPostCard {...BASE_PROPS} createdAt="" />,
    );
    expect(container.querySelector("time")).toBeNull();
    expect(screen.queryByText(/Invalid Date/)).not.toBeInTheDocument();
  });

  // Scenario: A missing image does not render a broken image
  it("keeps the text when the image fails", () => {
    const { container } = render(<NeonBlogPostCard {...BASE_PROPS} />);
    const img = container.querySelector("img");
    expect(img).not.toBeNull();
    fireEvent.error(img!);
    expect(container.querySelector("img")).toBeNull();
    expect(screen.getByText("A post")).toBeInTheDocument();
    expect(screen.getByText("AI models")).toBeInTheDocument();
  });

  it("renders without image, niche or subtitle", () => {
    const { container } = render(
      <NeonBlogPostCard
        {...BASE_PROPS}
        imageUrl={undefined}
        niche={undefined}
        subtitle={undefined}
        featured
      />,
    );
    expect(container.querySelector("img")).toBeNull();
    expect(screen.queryByText("AI models")).not.toBeInTheDocument();
    expect(screen.getByRole("link")).toHaveAttribute("href", "/blog/post-1");
  });
});
