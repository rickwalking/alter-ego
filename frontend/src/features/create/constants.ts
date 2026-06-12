import { BG_CARD, NEON_RED, TEXT, TEXT_DIM } from "@/constants/neon";

export const FAILED_CARD_STYLE = {
  background: BG_CARD,
  border: `1px solid ${NEON_RED}44`,
  borderRadius: "8px",
  padding: "24px",
} as const;

export const FAILED_CARD_HEADER_STYLE = {
  display: "flex",
  alignItems: "center",
  gap: "8px",
  marginBottom: "12px",
} as const;

export const FAILED_CARD_DOT_STYLE = {
  width: "10px",
  height: "10px",
  borderRadius: "50%",
  background: NEON_RED,
  flexShrink: 0 as const,
} as const;

export const FAILED_CARD_PHASE_LABEL_KEY: Record<string, string> = {
  research: "sendBack.phases.research",
  outline: "sendBack.phases.outline",
  content: "sendBack.phases.content",
  design: "sendBack.phases.design",
  images: "sendBack.phases.images",
  final_review: "review.finalReview.title",
};

export const FAILED_CARD_COLORS = {
  NEON_RED,
  TEXT,
  TEXT_DIM,
} as const;
