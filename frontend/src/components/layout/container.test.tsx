import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Container } from "./container";

describe("Container Component", () => {
  describe("Given the Container component is rendered", () => {
    describe("When the Container contains children", () => {
      it("Then the children should be rendered inside the Container", () => {
        render(
          <Container data-testid="container">
            <p>Content</p>
          </Container>
        );
        expect(screen.getByTestId("container")).toBeInTheDocument();
        expect(screen.getByText("Content")).toBeInTheDocument();
      });
    });

    describe("When the Container is rendered with default styling", () => {
      it("Then it should have responsive padding classes", () => {
        render(<Container data-testid="container">Content</Container>);
        const container = screen.getByTestId("container");
        expect(container).toHaveClass("px-4");
        expect(container).toHaveClass("sm:px-6");
        expect(container).toHaveClass("lg:px-8");
      });

      it("Then it should have max-width class", () => {
        render(<Container data-testid="container">Content</Container>);
        expect(screen.getByTestId("container")).toHaveClass("max-w-7xl");
      });

      it("Then it should be centered with mx-auto", () => {
        render(<Container data-testid="container">Content</Container>);
        expect(screen.getByTestId("container")).toHaveClass("mx-auto");
      });

      it("Then it should have full width", () => {
        render(<Container data-testid="container">Content</Container>);
        expect(screen.getByTestId("container")).toHaveClass("w-full");
      });
    });

    describe("When a custom className is provided", () => {
      it("Then the custom class should be applied to the Container", () => {
        render(
          <Container className="custom-class" data-testid="container">
            Content
          </Container>
        );
        expect(screen.getByTestId("container")).toHaveClass("custom-class");
      });
    });

    describe("When the Container has multiple children", () => {
      it("Then all children should be rendered", () => {
        render(
          <Container data-testid="container">
            <div>Child 1</div>
            <div>Child 2</div>
            <div>Child 3</div>
          </Container>
        );
        expect(screen.getByText("Child 1")).toBeInTheDocument();
        expect(screen.getByText("Child 2")).toBeInTheDocument();
        expect(screen.getByText("Child 3")).toBeInTheDocument();
      });
    });

    describe("When the Container wraps complex content", () => {
      it("Then nested elements should be rendered correctly", () => {
        render(
          <Container data-testid="container">
            <header>
              <h1>Title</h1>
            </header>
            <main>
              <p>Main content</p>
            </main>
            <footer>
              <span>Footer</span>
            </footer>
          </Container>
        );
        expect(screen.getByRole("heading", { name: /title/i })).toBeInTheDocument();
        expect(screen.getByText("Main content")).toBeInTheDocument();
        expect(screen.getByText("Footer")).toBeInTheDocument();
      });
    });
  });
});
