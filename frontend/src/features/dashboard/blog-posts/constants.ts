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
  security: { bg: "rgba(255,39,112,0.12)", text: "#ff2770" },
  ai: { bg: "rgba(10,197,168,0.12)", text: "#0ac5a8" },
  architecture: { bg: "rgba(168,85,247,0.12)", text: "#a855f7" },
  dev: { bg: "rgba(245,158,11,0.12)", text: "#f59e0b" },
  magenta: { bg: "rgba(255,39,112,0.12)", text: "#ff2770" },
  teal: { bg: "rgba(10,197,168,0.12)", text: "#0ac5a8" },
  cyan: { bg: "rgba(0,212,255,0.12)", text: "#00d4ff" },
  purple: { bg: "rgba(168,85,247,0.12)", text: "#a855f7" },
  amber: { bg: "rgba(245,158,11,0.12)", text: "#f59e0b" },
  red: { bg: "rgba(239,68,68,0.12)", text: "#ef4444" },
  featured: { bg: "rgba(0,212,255,0.12)", text: "#00d4ff" },
};

export const BLOG_POST_BADGE_CLASS = "badge";
