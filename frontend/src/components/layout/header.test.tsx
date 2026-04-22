import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { Header } from "./header";

const NAV_LABELS: Record<string, string> = {
  appName: "RAG Chat",
  "nav.chat": "Chat",
  "nav.knowledgeBase": "Knowledge Base",
  "nav.blog": "Blog",
  "nav.create": "Create",
};

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => NAV_LABELS[key] ?? key,
}));

// Mock next/link
vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    className,
  }: {
    children: React.ReactNode;
    href: string;
    className?: string;
  }) => (
    <a href={href} className={className}>
      {children}
    </a>
  ),
}));

describe("Header Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Given the Header component is rendered", () => {
    describe("When the Header is displayed", () => {
      it("Then the logo text should be visible", () => {
        render(<Header />);
        expect(screen.getByText("RAG Chat")).toBeInTheDocument();
      });

      it("Then the logo should link to the home page", () => {
        render(<Header />);
        const logo = screen.getByText("RAG Chat").closest("a");
        expect(logo).toHaveAttribute("href", "/");
      });
    });

    describe("When the navigation links are present", () => {
      it("Then the Chat link should be visible", () => {
        render(<Header />);
        expect(screen.getByText("Chat")).toBeInTheDocument();
      });

      it("Then the Chat link should link to /chat", () => {
        render(<Header />);
        const chatLink = screen.getByText("Chat").closest("a");
        expect(chatLink).toHaveAttribute("href", "/chat");
      });

      it("Then the Knowledge Base link should be visible", () => {
        render(<Header />);
        expect(screen.getByText("Knowledge Base")).toBeInTheDocument();
      });

      it("Then the Knowledge Base link should link to /knowledge", () => {
        render(<Header />);
        const knowledgeLink = screen.getByText("Knowledge Base").closest("a");
        expect(knowledgeLink).toHaveAttribute("href", "/knowledge");
      });
    });

    describe("When the Header has default styling", () => {
      it("Then it should have sticky positioning", () => {
        render(<Header />);
        const header = screen.getByRole("banner");
        expect(header).toHaveClass("sticky");
        expect(header).toHaveClass("top-0");
      });

      it("Then it should have backdrop blur effect", () => {
        render(<Header />);
        const header = screen.getByRole("banner");
        expect(header).toHaveClass("backdrop-blur");
      });

      it("Then it should have a border", () => {
        render(<Header />);
        const header = screen.getByRole("banner");
        expect(header).toHaveClass("border-b");
      });
    });

    describe("When the navigation is displayed on different screen sizes", () => {
      it("Then the navigation should be hidden on mobile", () => {
        render(<Header />);
        const nav = screen.getByText("Chat").closest("nav");
        expect(nav).toHaveClass("hidden");
        expect(nav).toHaveClass("md:flex");
      });
    });
  });
});
