import { BG_CARD, NEON_CYAN, NEON_CYAN_DIM } from "@/constants/neon";

export const CYAN = NEON_CYAN;
export const CYAN_DIM = NEON_CYAN_DIM;

export const SECTION_CARD_STYLE = {
  background: BG_CARD,
  border: "1px solid rgba(255,255,255,0.06)",
  borderRadius: "8px",
  padding: "24px",
} as const;
