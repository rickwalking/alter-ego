import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  Card,
  CardHeader,
  CardFooter,
  CardTitle,
  CardDescription,
  CardContent,
} from "./card";

describe("Card Component", () => {
  describe("Given the Card component is rendered", () => {
    describe("When the Card contains child content", () => {
      it("Then the Card should display the content", () => {
        render(
          <Card data-testid="card">
            <p>Card content</p>
          </Card>,
        );
        expect(screen.getByTestId("card")).toBeInTheDocument();
        expect(screen.getByText("Card content")).toBeInTheDocument();
      });
    });

    describe("When a custom className is provided", () => {
      it("Then the custom class should be applied to the Card", () => {
        render(<Card className="custom-class" data-testid="card" />);
        expect(screen.getByTestId("card")).toHaveClass("custom-class");
      });
    });

    describe("When the Card has default styling", () => {
      it("Then it should have the base card classes", () => {
        render(<Card data-testid="card" />);
        const card = screen.getByTestId("card");
        expect(card).toHaveClass("rounded-lg");
        expect(card).toHaveClass("border");
        expect(card).toHaveClass("shadow-sm");
      });
    });
  });

  describe("Given the CardHeader component is rendered", () => {
    describe("When the CardHeader contains content", () => {
      it("Then the CardHeader should display the content", () => {
        render(
          <CardHeader data-testid="header">
            <p>Header content</p>
          </CardHeader>,
        );
        expect(screen.getByTestId("header")).toBeInTheDocument();
        expect(screen.getByText("Header content")).toBeInTheDocument();
      });
    });

    describe("When a custom className is provided", () => {
      it("Then the custom class should be applied to the CardHeader", () => {
        render(<CardHeader className="custom-header" data-testid="header" />);
        expect(screen.getByTestId("header")).toHaveClass("custom-header");
      });
    });
  });

  describe("Given the CardTitle component is rendered", () => {
    describe("When the CardTitle contains text", () => {
      it("Then the title should be rendered as an h3 element", () => {
        render(<CardTitle>Card Title</CardTitle>);
        expect(
          screen.getByRole("heading", { name: /card title/i }),
        ).toBeInTheDocument();
      });
    });

    describe("When a custom className is provided", () => {
      it("Then the custom class should be applied to the CardTitle", () => {
        render(<CardTitle className="custom-title">Title</CardTitle>);
        expect(screen.getByRole("heading")).toHaveClass("custom-title");
      });
    });

    describe("When rendered with default styling", () => {
      it("Then it should have the title styling classes", () => {
        render(<CardTitle>Title</CardTitle>);
        const title = screen.getByRole("heading");
        expect(title).toHaveClass("text-2xl");
        expect(title).toHaveClass("font-semibold");
      });
    });
  });

  describe("Given the CardDescription component is rendered", () => {
    describe("When the CardDescription contains text", () => {
      it("Then the description text should be displayed", () => {
        render(<CardDescription>Description text</CardDescription>);
        expect(screen.getByText("Description text")).toBeInTheDocument();
      });
    });

    describe("When a custom className is provided", () => {
      it("Then the custom class should be applied to the CardDescription", () => {
        render(
          <CardDescription className="custom-desc">
            Description
          </CardDescription>,
        );
        expect(screen.getByText("Description")).toHaveClass("custom-desc");
      });
    });

    describe("When rendered with default styling", () => {
      it("Then it should have the description styling classes", () => {
        render(<CardDescription>Description</CardDescription>);
        const desc = screen.getByText("Description");
        expect(desc).toHaveClass("text-sm");
      });
    });
  });

  describe("Given the CardContent component is rendered", () => {
    describe("When the CardContent contains content", () => {
      it("Then the content should be displayed", () => {
        render(
          <CardContent data-testid="content">
            <p>Content here</p>
          </CardContent>,
        );
        expect(screen.getByTestId("content")).toBeInTheDocument();
      });
    });

    describe("When a custom className is provided", () => {
      it("Then the custom class should be applied to the CardContent", () => {
        render(
          <CardContent className="custom-content" data-testid="content" />,
        );
        expect(screen.getByTestId("content")).toHaveClass("custom-content");
      });
    });
  });

  describe("Given the CardFooter component is rendered", () => {
    describe("When the CardFooter contains content", () => {
      it("Then the footer content should be displayed", () => {
        render(
          <CardFooter data-testid="footer">
            <button>Action</button>
          </CardFooter>,
        );
        expect(screen.getByTestId("footer")).toBeInTheDocument();
        expect(screen.getByRole("button")).toBeInTheDocument();
      });
    });

    describe("When a custom className is provided", () => {
      it("Then the custom class should be applied to the CardFooter", () => {
        render(<CardFooter className="custom-footer" data-testid="footer" />);
        expect(screen.getByTestId("footer")).toHaveClass("custom-footer");
      });
    });
  });

  describe("Given a complete Card structure is rendered", () => {
    describe("When all subcomponents are used together", () => {
      it("Then the complete Card should render with all sections", () => {
        render(
          <Card>
            <CardHeader>
              <CardTitle>Test Card</CardTitle>
              <CardDescription>A test description</CardDescription>
            </CardHeader>
            <CardContent>
              <p>Main content</p>
            </CardContent>
            <CardFooter>
              <button>Submit</button>
            </CardFooter>
          </Card>,
        );

        expect(
          screen.getByRole("heading", { name: /test card/i }),
        ).toBeInTheDocument();
        expect(screen.getByText("A test description")).toBeInTheDocument();
        expect(screen.getByText("Main content")).toBeInTheDocument();
        expect(
          screen.getByRole("button", { name: /submit/i }),
        ).toBeInTheDocument();
      });
    });
  });
});
