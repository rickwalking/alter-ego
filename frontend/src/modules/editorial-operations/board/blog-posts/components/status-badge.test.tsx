import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BLOG_POST_STATUSES } from "@/modules/publishing";
import {
  BLOG_POST_BADGE_FALLBACK,
  BLOG_POST_STATUS_COLORS,
} from "../constants";
import { BlogPostStatusBadge } from "./status-badge";

// Scenarios: see tests/features/blog-posts-listing-status-badge.feature
// ("Status badge shows a distinct label and color per status",
//  "Unknown backend status renders a neutral badge instead of crashing")

describe("BLOG_POST_STATUS_COLORS", () => {
  it("covers exactly the BlogPostStatus vocabulary", () => {
    expect(Object.keys(BLOG_POST_STATUS_COLORS).sort()).toEqual(
      [...BLOG_POST_STATUSES].sort(),
    );
  });

  it("defines a non-empty bg and text for every status", () => {
    for (const status of BLOG_POST_STATUSES) {
      const visual = BLOG_POST_STATUS_COLORS[status];
      expect(visual.bg).toBeTruthy();
      expect(visual.text).toBeTruthy();
    }
  });
});

describe("BlogPostStatusBadge", () => {
  it("renders every status without throwing, with its localized label", () => {
    const labels: Record<string, string> = {
      draft: "Draft",
      under_review: "Under Review",
      approved: "Approved",
      published: "Published",
      archived: "Archived",
    };
    for (const status of BLOG_POST_STATUSES) {
      const { unmount } = render(<BlogPostStatusBadge status={status} />);
      expect(screen.getByText(labels[status])).toBeInTheDocument();
      unmount();
    }
  });

  it("visually distinguishes draft from published", () => {
    render(<BlogPostStatusBadge status="draft" />);
    render(<BlogPostStatusBadge status="published" />);
    const draft = screen.getByText("Draft");
    const published = screen.getByText("Published");
    expect(BLOG_POST_STATUS_COLORS.draft.text).not.toBe(
      BLOG_POST_STATUS_COLORS.published.text,
    );
    expect(draft).toHaveStyle({ color: BLOG_POST_STATUS_COLORS.draft.text });
    expect(published).toHaveStyle({
      color: BLOG_POST_STATUS_COLORS.published.text,
    });
  });

  it("renders the neutral fallback for a null (unknown/drifted) status", () => {
    expect(() => render(<BlogPostStatusBadge status={null} />)).not.toThrow();
    const badge = screen.getByText("Unknown");
    expect(badge).toHaveStyle({
      backgroundColor: BLOG_POST_BADGE_FALLBACK.bg,
    });
  });
});
