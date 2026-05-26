import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { Header } from "./header";

const NAV_LABELS: Record<string, string> = {
  appName: "Pedro Marins",
  "nav.chat": "Chat",
  "nav.knowledgeBase": "Knowledge Base",
  "nav.blog": "Blog",
  "nav.create": "Create",
  "nav.personas": "Personas",
  "nav.rubrics": "Rubrics",
  "nav.blogPosts": "Blog Posts",
  "nav.workflow": "Workflow",
  "nav.calendar": "Calendar",
  "nav.analytics": "Analytics",
  logout: "Logout",
  "nav.admin": "Admin",
  login: "Login",
};

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => NAV_LABELS[key] ?? key,
}));

vi.mock("@/components/language-switcher", () => ({
  LanguageSwitcher: ({ currentLocale }: { currentLocale: string }) => (
    <div data-testid="language-switcher">{currentLocale}</div>
  ),
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

const mockUseAuth = vi.fn();
vi.mock("@/hooks/use-auth", () => ({
  useAuth: () => mockUseAuth(),
}));

function mockAnonymous() {
  mockUseAuth.mockReturnValue({
    user: null,
    isAdmin: false,
    isEditor: false,
    isLoading: false,
    logout: vi.fn(),
  });
}

function mockEditor() {
  mockUseAuth.mockReturnValue({
    user: {
      id: "1",
      email: "editor@test.com",
      full_name: "Editor",
      role: "editor",
    },
    isAdmin: false,
    isEditor: true,
    isLoading: false,
    logout: vi.fn(),
  });
}

function mockAdmin() {
  mockUseAuth.mockReturnValue({
    user: {
      id: "1",
      email: "admin@test.com",
      full_name: "Admin",
      role: "admin",
    },
    isAdmin: true,
    isEditor: true,
    isLoading: false,
    logout: vi.fn(),
  });
}

describe("Header Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAnonymous();
  });

  describe("Given the Header component is rendered", () => {
    describe("When the Header is displayed", () => {
      it("Then the logo text should be visible", () => {
        render(<Header locale="en" />);
        expect(screen.getByText("Pedro Marins")).toBeInTheDocument();
      });

      it("Then the logo should link to the home page", () => {
        render(<Header locale="en" />);
        const logo = screen.getByText("Pedro Marins").closest("a");
        expect(logo).toHaveAttribute("href", "/");
      });
    });

    describe("When the user is anonymous", () => {
      it("Then Chat and Blog links should be visible, others hidden", () => {
        render(<Header locale="en" />);
        expect(screen.getByText("Blog")).toBeInTheDocument();
        expect(screen.getByText("Chat")).toBeInTheDocument();
        expect(screen.queryByText("Knowledge Base")).not.toBeInTheDocument();
        expect(screen.queryByText("Create")).not.toBeInTheDocument();
        expect(screen.queryByText("Admin")).not.toBeInTheDocument();
      });

      it("Then the Login link should be visible", () => {
        render(<Header locale="en" />);
        expect(screen.getByText("Login")).toBeInTheDocument();
      });
    });

    describe("When the user is an editor", () => {
      beforeEach(() => {
        mockEditor();
      });

      it("Then Chat, Knowledge Base, Blog, and Create links should be visible", () => {
        render(<Header locale="en" />);
        expect(screen.getByText("Chat")).toBeInTheDocument();
        expect(screen.getByText("Knowledge Base")).toBeInTheDocument();
        expect(screen.getByText("Blog")).toBeInTheDocument();
        expect(screen.getByText("Create")).toBeInTheDocument();
      });

      it("Then the Admin link should NOT be visible", () => {
        render(<Header locale="en" />);
        expect(screen.queryByText("Admin")).not.toBeInTheDocument();
      });

      it("Then the Logout button should be visible", () => {
        render(<Header locale="en" />);
        expect(screen.getByText("Logout")).toBeInTheDocument();
      });
    });

    describe("When the user is an admin", () => {
      beforeEach(() => {
        mockAdmin();
      });

      it("Then all nav links including Admin should be visible", () => {
        render(<Header locale="en" />);
        expect(screen.getByText("Chat")).toBeInTheDocument();
        expect(screen.getByText("Knowledge Base")).toBeInTheDocument();
        expect(screen.getByText("Blog")).toBeInTheDocument();
        expect(screen.getByText("Create")).toBeInTheDocument();
        expect(screen.getByText("Admin")).toBeInTheDocument();
      });

      it("Then the Chat link should link to /chat", () => {
        render(<Header locale="en" />);
        const chatLink = screen.getByText("Chat").closest("a");
        expect(chatLink).toHaveAttribute("href", "/chat");
      });

      it("Then the Knowledge Base link should link to /knowledge", () => {
        render(<Header locale="en" />);
        const knowledgeLink = screen.getByText("Knowledge Base").closest("a");
        expect(knowledgeLink).toHaveAttribute("href", "/knowledge");
      });
    });

    describe("When the Header has default styling", () => {
      it("Then it should have sticky positioning", () => {
        render(<Header locale="en" />);
        const header = screen.getByRole("banner");
        expect(header).toHaveClass("sticky");
        expect(header).toHaveClass("top-0");
      });

      it("Then it should have backdrop blur effect", () => {
        render(<Header locale="en" />);
        const header = screen.getByRole("banner");
        expect(header).toHaveClass("backdrop-blur");
      });

      it("Then it should have a border", () => {
        render(<Header locale="en" />);
        const header = screen.getByRole("banner");
        expect(header).toHaveClass("border-b");
      });
    });

    describe("When the navigation is displayed on different screen sizes", () => {
      it("Then the navigation should be hidden on mobile", () => {
        mockAdmin();
        render(<Header locale="en" />);
        const nav = screen.getByText("Chat").closest("nav");
        expect(nav).toHaveClass("hidden");
        expect(nav).toHaveClass("md:flex");
      });
    });
  });
});
