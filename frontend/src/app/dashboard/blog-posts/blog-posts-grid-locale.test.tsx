import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { DashboardBlogPost } from "@/modules/editorial-operations";
import { RegularBlogPosts } from "@/app/dashboard/blog-posts/blog-posts-grid";
import type { BlogPostActionHandlers } from "@/app/dashboard/blog-posts/types";

// Feature: Dashboard dates follow the active locale (AE-0417)
// tests/features/dashboard-locale-dates-ae0417.feature

const intl = vi.hoisted(() => ({ locale: "pt" }));

vi.mock("next-intl", () => ({
  useLocale: () => intl.locale,
  useTranslations: () => (key: string) => key,
}));

const NOOP_ACTIONS: BlogPostActionHandlers = {
  onDelete: () => undefined,
  onHide: () => undefined,
};

const POST: DashboardBlogPost = {
  id: "post-1",
  title: "Agentes que entregam",
  excerpt: "Resumo",
  date: new Date(2026, 9, 17, 12, 0).toISOString(),
  views: 1234,
  comments: 2,
  status: "draft",
  origin: "standalone",
  lockVersion: 1,
  isPublic: true,
};

describe("blog post card date (AE-0417)", () => {
  afterEach(() => {
    intl.locale = "pt";
  });

  // Scenario: Posts do Blog cards show the date in Portuguese
  it("shows the date and views in Portuguese in the pt UI", () => {
    render(<RegularBlogPosts posts={[POST]} actions={NOOP_ACTIONS} />);
    expect(screen.getByText("17/10/2026")).toBeInTheDocument();
    expect(screen.queryByText("Oct 17, 2026")).not.toBeInTheDocument();
    expect(screen.getByText(/1\.234/)).toBeInTheDocument();
  });

  // Scenario: Blog cards keep the English format in the English UI
  it("keeps the English format in the en UI", () => {
    intl.locale = "en";
    render(<RegularBlogPosts posts={[POST]} actions={NOOP_ACTIONS} />);
    expect(screen.getByText("Oct 17, 2026")).toBeInTheDocument();
    expect(screen.getByText(/1,234/)).toBeInTheDocument();
  });
});
