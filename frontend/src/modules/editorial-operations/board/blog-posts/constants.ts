import {
  NEON_AMBER,
  NEON_AMBER_DIM,
  NEON_CYAN,
  NEON_CYAN_DIM,
  NEON_GREEN,
  NEON_GREEN_BADGE_BG,
  NEON_MAGENTA,
  NEON_MAGENTA_DIM,
  NEON_PURPLE,
  NEON_RED,
  NEON_TEAL,
  NEON_TEAL_DIM,
} from "@/constants/neon";
import type { BlogPostStatus } from "@/modules/publishing";
import { BLOG_POST_STATUSES } from "@/modules/publishing";
import type { BlogPostBadgeVisual } from "./types";

const NEON_PURPLE_BADGE_BG = "rgba(168,85,247,0.12)";
const NEON_RED_BADGE_BG = "rgba(239,68,68,0.12)";
const NEUTRAL_BADGE_BG = "rgba(255,255,255,0.08)";
const NEUTRAL_BADGE_TEXT = "rgba(255,255,255,0.7)";

export const BLOG_POST_STATUS_FILTER_VALUES = BLOG_POST_STATUSES;

export const BLOG_POST_CATEGORY_OPTIONS = [
  { value: "", label: "All Categories" },
  { value: "AI", label: "AI" },
  { value: "Security", label: "Security" },
  { value: "Architecture", label: "Architecture" },
  { value: "Dev", label: "Dev" },
] as const;

export const BLOG_POST_BADGE_COLORS: Record<string, BlogPostBadgeVisual> = {
  security: { bg: NEON_MAGENTA_DIM, text: NEON_MAGENTA },
  ai: { bg: NEON_TEAL_DIM, text: NEON_TEAL },
  architecture: { bg: NEON_PURPLE_BADGE_BG, text: NEON_PURPLE },
  dev: { bg: NEON_AMBER_DIM, text: NEON_AMBER },
  magenta: { bg: NEON_MAGENTA_DIM, text: NEON_MAGENTA },
  teal: { bg: NEON_TEAL_DIM, text: NEON_TEAL },
  cyan: { bg: NEON_CYAN_DIM, text: NEON_CYAN },
  purple: { bg: NEON_PURPLE_BADGE_BG, text: NEON_PURPLE },
  amber: { bg: NEON_AMBER_DIM, text: NEON_AMBER },
  red: { bg: NEON_RED_BADGE_BG, text: NEON_RED },
  featured: { bg: NEON_CYAN_DIM, text: NEON_CYAN },
};

/**
 * Neutral badge visual used when a badge color key is not in the palette map —
 * an unknown key must never crash the listing (AE-0295).
 */
export const BLOG_POST_BADGE_FALLBACK: BlogPostBadgeVisual = {
  bg: NEUTRAL_BADGE_BG,
  text: NEUTRAL_BADGE_TEXT,
};

/**
 * Workflow-status badge palette (AE-0295). Keyed by the complete
 * `BlogPostStatus` vocabulary — `Record<BlogPostStatus, …>` makes a missing
 * status a compile error, not a runtime crash. Distinct from the carousel
 * *workflow* status palette (`resolveWorkflowStatusVisual`); never conflate.
 */
export const BLOG_POST_STATUS_COLORS: Record<
  BlogPostStatus,
  BlogPostBadgeVisual
> = {
  draft: { bg: NEON_AMBER_DIM, text: NEON_AMBER },
  under_review: { bg: NEON_PURPLE_BADGE_BG, text: NEON_PURPLE },
  approved: { bg: NEON_TEAL_DIM, text: NEON_TEAL },
  published: { bg: NEON_GREEN_BADGE_BG, text: NEON_GREEN },
  archived: { bg: NEUTRAL_BADGE_BG, text: NEUTRAL_BADGE_TEXT },
};

export const BLOG_POST_BADGE_CLASS = "badge";

export const BLOG_POSTS_I18N_NAMESPACE = "dashboard.blogPosts";
