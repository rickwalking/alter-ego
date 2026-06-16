import {
  NEON_AMBER,
  NEON_AMBER_DIM,
  NEON_CYAN,
  NEON_CYAN_DIM,
  NEON_MAGENTA,
  NEON_MAGENTA_DIM,
  NEON_PURPLE,
  NEON_RED,
  NEON_TEAL,
  NEON_TEAL_DIM,
} from "@/constants/neon";

export const BLOG_POST_STATUS_OPTIONS = [
  { value: "", label: "All Status" },
  { value: "published", label: "Published" },
  { value: "draft", label: "Draft" },
  { value: "review", label: "Review" },
] as const;

export const BLOG_POST_CATEGORY_OPTIONS = [
  { value: "", label: "All Categories" },
  { value: "AI", label: "AI" },
  { value: "Security", label: "Security" },
  { value: "Architecture", label: "Architecture" },
  { value: "Dev", label: "Dev" },
] as const;

export const BLOG_POST_BADGE_COLORS: Record<
  string,
  { bg: string; text: string }
> = {
  security: { bg: NEON_MAGENTA_DIM, text: NEON_MAGENTA },
  ai: { bg: NEON_TEAL_DIM, text: NEON_TEAL },
  architecture: { bg: "rgba(168,85,247,0.12)", text: NEON_PURPLE },
  dev: { bg: NEON_AMBER_DIM, text: NEON_AMBER },
  magenta: { bg: NEON_MAGENTA_DIM, text: NEON_MAGENTA },
  teal: { bg: NEON_TEAL_DIM, text: NEON_TEAL },
  cyan: { bg: NEON_CYAN_DIM, text: NEON_CYAN },
  purple: { bg: "rgba(168,85,247,0.12)", text: NEON_PURPLE },
  amber: { bg: NEON_AMBER_DIM, text: NEON_AMBER },
  red: { bg: "rgba(239,68,68,0.12)", text: NEON_RED },
  featured: { bg: NEON_CYAN_DIM, text: NEON_CYAN },
};

export const BLOG_POST_BADGE_CLASS = "badge";
