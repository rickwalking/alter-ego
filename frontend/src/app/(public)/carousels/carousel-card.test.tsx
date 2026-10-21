import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CarouselCard } from "./carousel-card";
import type { PublicCarouselCard } from "@/lib/public-carousels";

const CARD: PublicCarouselCard = {
  id: "proj-1",
  title: "IA sem hype",
  createdAt: "2026-10-20T11:40:01Z",
  language: "pt-BR",
  slideCount: 7,
  href: "/carousels/proj-1",
  coverUrl: "/api/carousels/proj-1/images/slide_1.jpg",
};

const LABELS = {
  slides: "7 slides",
  open: "Abrir carrossel: IA sem hype",
  view: "Ver carrossel",
  coverAlt: "Capa de IA sem hype",
};

describe("CarouselCard (AE-0444)", () => {
  it("renders the cover, title, language, date and slide count", () => {
    render(<CarouselCard card={CARD} labels={LABELS} locale="pt" />);

    expect(screen.getByAltText("Capa de IA sem hype")).toBeInTheDocument();
    expect(screen.getByText("IA sem hype")).toBeInTheDocument();
    expect(screen.getByText("PT")).toBeInTheDocument();
    expect(screen.getByText("7 slides")).toBeInTheDocument();
    expect(screen.getByRole("link")).toHaveAttribute(
      "href",
      "/carousels/proj-1",
    );
    expect(screen.getByRole("link")).toHaveAccessibleName(LABELS.open);
  });

  it("renders the placeholder and hides missing metadata", () => {
    render(
      <CarouselCard
        card={{ ...CARD, coverUrl: null, slideCount: null }}
        labels={LABELS}
        locale="en"
      />,
    );

    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(screen.queryByText("7 slides")).not.toBeInTheDocument();
    expect(screen.getByText("IA sem hype")).toBeInTheDocument();
  });
});
