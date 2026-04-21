import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { CarouselPreview } from "./carousel-preview";
import type { CarouselProjectResponse } from "@/schemas/carousel";

vi.mock("next-intl", () => ({
  useTranslations: vi.fn(() => {
    const translations: Record<string, string> = {
      "preview.viewBlog": "View Blog Post",
    };
    return (key: string) => translations[key] ?? key;
  }),
}));

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    className,
  }: {
    href: string;
    children: React.ReactNode;
    className?: string;
  }) => (
    <a href={href} className={className} data-testid="blog-link">
      {children}
    </a>
  ),
}));

describe("CarouselPreview Component", () => {
  const mockProject: CarouselProjectResponse = {
    id: "abc-123",
    topic: "React Testing",
    audience: "Developers",
    niche: "Frontend",
    title: "Mastering React Testing",
    subtitle: "A comprehensive guide",
    theme: "developer_skills",
    status: "completed",
    blog_markdown: "# Content",
    blog_translations: { en: "# Content" },
    caption: "Check this out!",
    design_tokens: null,
    created_at: "2026-04-20T00:00:00Z",
    updated_at: "2026-04-20T00:00:00Z",
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Given the CarouselPreview is rendered with a project", () => {
    describe("When the project has a title", () => {
      it("Then the title should be displayed", () => {
        render(<CarouselPreview project={mockProject} />);
        expect(screen.getByText("Mastering React Testing")).toBeInTheDocument();
      });

      it("Then the topic should not be displayed as the title", () => {
        render(<CarouselPreview project={mockProject} />);
        expect(screen.queryByText("React Testing")).not.toBeInTheDocument();
      });
    });

    describe("When the project has no title but has a topic", () => {
      it("Then the topic should be displayed as the title", () => {
        const projectWithoutTitle = { ...mockProject, title: null };
        render(<CarouselPreview project={projectWithoutTitle} />);
        expect(screen.getByText("React Testing")).toBeInTheDocument();
      });
    });

    describe("When the project has a subtitle", () => {
      it("Then the subtitle should be displayed", () => {
        render(<CarouselPreview project={mockProject} />);
        expect(screen.getByText("A comprehensive guide")).toBeInTheDocument();
      });
    });

    describe("When the project has no subtitle", () => {
      it("Then no subtitle should be displayed", () => {
        const projectWithoutSubtitle = { ...mockProject, subtitle: null };
        render(<CarouselPreview project={projectWithoutSubtitle} />);
        expect(screen.queryByText(/comprehensive/i)).not.toBeInTheDocument();
      });
    });

    describe("When the project has a niche", () => {
      it("Then the niche should be displayed as a badge", () => {
        render(<CarouselPreview project={mockProject} />);
        expect(screen.getByText("Frontend")).toBeInTheDocument();
      });
    });

    describe("When the blog link is rendered", () => {
      it("Then the link should point to the blog post route", () => {
        render(<CarouselPreview project={mockProject} />);
        const link = screen.getByTestId("blog-link");
        expect(link).toHaveAttribute("href", "/blog/abc-123");
      });

      it("Then the link text should use the i18n key", () => {
        render(<CarouselPreview project={mockProject} />);
        expect(screen.getByText("View Blog Post")).toBeInTheDocument();
      });
    });
  });

  describe("Given the project has design tokens with a hero image", () => {
    describe("When design_tokens contains a hero image", () => {
      it("Then the hero image should be displayed", () => {
        const projectWithImage: CarouselProjectResponse = {
          ...mockProject,
          design_tokens: {
            images: {
              hero: "/api/carousels/abc-123/images/slide_1",
              slides: [],
            },
          },
        };
        render(<CarouselPreview project={projectWithImage} />);
        const img = screen.getByRole("img", {
          name: "Mastering React Testing",
        });
        expect(img).toBeInTheDocument();
        // `hero` is already a full API path — the component uses it as-is
        // (optionally prefixed with NEXT_PUBLIC_API_URL). No extra
        // "/api/carousels/{id}/images/" prefixing.
        expect(img).toHaveAttribute(
          "src",
          "/api/carousels/abc-123/images/slide_1"
        );
      });

      it("Then the image alt text should use the title", () => {
        const projectWithImage: CarouselProjectResponse = {
          ...mockProject,
          design_tokens: {
            images: {
              hero: "/api/carousels/abc-123/images/slide_1",
              slides: [],
            },
          },
        };
        render(<CarouselPreview project={projectWithImage} />);
        const img = screen.getByRole("img", {
          name: "Mastering React Testing",
        });
        expect(img).toHaveAttribute("alt", "Mastering React Testing");
      });

      it("Then the image alt text should fall back to topic when title is null", () => {
        const projectWithImage: CarouselProjectResponse = {
          ...mockProject,
          title: null,
          design_tokens: {
            images: {
              hero: "hero.jpg",
              slides: [],
            },
          },
        };
        render(<CarouselPreview project={projectWithImage} />);
        const img = screen.getByRole("img", { name: "React Testing" });
        expect(img).toBeInTheDocument();
      });
    });

    describe("When design_tokens is null", () => {
      it("Then no image should be displayed", () => {
        const projectWithoutImage: CarouselProjectResponse = {
          ...mockProject,
          design_tokens: null,
        };
        render(<CarouselPreview project={projectWithoutImage} />);
        expect(screen.queryByRole("img")).not.toBeInTheDocument();
      });
    });

    describe("When design_tokens has no images", () => {
      it("Then no image should be displayed", () => {
        const projectWithoutImage: CarouselProjectResponse = {
          ...mockProject,
          design_tokens: {},
        };
        render(<CarouselPreview project={projectWithoutImage} />);
        expect(screen.queryByRole("img")).not.toBeInTheDocument();
      });
    });

    describe("When design_tokens images has no hero", () => {
      it("Then no image should be displayed", () => {
        const projectWithoutImage: CarouselProjectResponse = {
          ...mockProject,
          design_tokens: {
            images: {
              hero: "",
              slides: [],
            },
          },
        };
        render(<CarouselPreview project={projectWithoutImage} />);
        expect(screen.queryByRole("img")).not.toBeInTheDocument();
      });
    });
  });
});
