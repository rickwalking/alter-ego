import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CarouselNeighbors } from "./carousel-neighbors";

// Feature: Public carousel viewer (AE-0444)

describe("CarouselNeighbors (AE-0444)", () => {
  it("links previous, next and the gallery", () => {
    render(
      <CarouselNeighbors
        previous={{ id: "a", title: "Anterior", href: "/carousels/a" }}
        next={{ id: "c", title: "Próximo", href: "/carousels/c" }}
        previousLabel="Anterior"
        nextLabel="Próximo"
        listLabel="Todos os carrosséis"
        listHref="/carousels"
      />,
    );

    expect(
      screen.getByRole("link", { name: "Anterior: Anterior" }),
    ).toHaveAttribute("href", "/carousels/a");
    expect(
      screen.getByRole("link", { name: "Próximo: Próximo" }),
    ).toHaveAttribute("href", "/carousels/c");
    expect(
      screen.getByRole("link", { name: "Todos os carrosséis" }),
    ).toHaveAttribute("href", "/carousels");
  });

  it("renders only the gallery link at the edges", () => {
    render(
      <CarouselNeighbors
        previous={null}
        next={null}
        previousLabel="Anterior"
        nextLabel="Próximo"
        listLabel="Todos os carrosséis"
        listHref="/carousels"
      />,
    );

    expect(screen.getAllByRole("link")).toHaveLength(1);
  });
});
