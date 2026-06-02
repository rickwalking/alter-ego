import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BlogPostAdminPanel } from "./blog-post-admin-panel";

// Feature: Blog post admin panel
//   As a content author
//   I want to delete or publish a blog post from the post page
//   So that I can manage my content without navigating away

const mockDesign = {
  colors: {
    primary: "#3b82f6",
    accent: "#f59e0b",
    bg: "#0a0e17",
    text: "#e2e8f0",
    text_muted: "#64748b",
    text_dim: "#94a3b8",
    border: "#1e293b",
    glow: "#3b82f6",
  },
  typography: {
    font_family_heading: "Inter",
    font_family_body: "Inter",
    font_family_badge: "monospace",
  },
  images: {
    hero: "/hero.jpg",
    slides: [],
    rendered_slides_pt: [],
    rendered_slides_en: [],
  },
  layout: {
    badge_label: "AI",
    swipe_text: "Swipe",
    progress_segments: 5,
  },
  theme_name: "ai_competition",
};

const mockTranslations: Record<string, string> = {
  "blog.admin.title": "Admin",
  "blog.admin.publish": "Publish",
  "blog.admin.delete": "Delete",
  "blog.admin.deleteConfirm": "Are you sure?",
  "blog.admin.deleteConfirmTitle": "Delete post",
  "blog.admin.cancel": "Cancel",
  "blog.admin.deleting": "Deleting...",
};

vi.mock("next-intl", () => ({
  useTranslations: (ns: string) => (key: string) =>
    mockTranslations[`${ns}.${key}`] ?? key,
}));

const mockMutateAsync = vi.fn();

vi.mock("@/features/create/hooks", () => ({
  useDeleteCarousel: () => ({
    mutateAsync: mockMutateAsync,
    isPending: false,
  }),
}));

const mockPush = vi.fn();
const mockRefresh = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, refresh: mockRefresh }),
}));

vi.mock("@/hooks/use-auth", () => ({
  useAuth: () => ({
    user: { id: "1", email: "admin@test.com" },
    isAdmin: true,
  }),
}));

describe("BlogPostAdminPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders publish and delete buttons", () => {
    render(<BlogPostAdminPanel projectId="abc123" design={mockDesign} />);

    expect(screen.getByText("Admin")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Publish/i })).toHaveAttribute(
      "href",
      "/dashboard/create/abc123/publish",
    );
    expect(screen.getByRole("button", { name: /Delete/i })).toBeInTheDocument();
  });

  it("opens confirmation dialog when delete is clicked", async () => {
    const user = userEvent.setup();
    render(<BlogPostAdminPanel projectId="abc123" design={mockDesign} />);

    await user.click(screen.getByRole("button", { name: /Delete/i }));

    expect(screen.getByText("Delete post")).toBeInTheDocument();
    expect(screen.getByText("Are you sure?")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Cancel/i })).toBeInTheDocument();
  });

  it("closes confirmation dialog when cancel is clicked", async () => {
    const user = userEvent.setup();
    render(<BlogPostAdminPanel projectId="abc123" design={mockDesign} />);

    await user.click(screen.getByRole("button", { name: /Delete/i }));
    await user.click(screen.getByRole("button", { name: /Cancel/i }));

    expect(screen.queryByText("Delete post")).not.toBeInTheDocument();
  });

  it("navigates to homepage after successful delete", async () => {
    const user = userEvent.setup();
    mockMutateAsync.mockResolvedValueOnce(undefined);
    render(<BlogPostAdminPanel projectId="abc123" design={mockDesign} />);

    await user.click(screen.getByRole("button", { name: /Delete/i }));
    const confirmButtons = screen.getAllByRole("button", { name: /Delete/i });
    await user.click(confirmButtons[confirmButtons.length - 1]);

    await waitFor(() => expect(mockMutateAsync).toHaveBeenCalledWith("abc123"));
    expect(mockPush).toHaveBeenCalledWith("/");
    expect(mockRefresh).toHaveBeenCalled();
    expect(screen.queryByText("Delete post")).not.toBeInTheDocument();
  });

  it("closes dialog even when delete fails", async () => {
    const user = userEvent.setup();
    mockMutateAsync.mockRejectedValueOnce(new Error("network error"));
    render(<BlogPostAdminPanel projectId="abc123" design={mockDesign} />);

    await user.click(screen.getByRole("button", { name: /Delete/i }));
    const confirmButtons = screen.getAllByRole("button", { name: /Delete/i });
    await user.click(confirmButtons[confirmButtons.length - 1]);

    await waitFor(() => expect(mockMutateAsync).toHaveBeenCalled());
    expect(screen.queryByText("Delete post")).not.toBeInTheDocument();
  });
});
