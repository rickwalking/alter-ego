import { BG_CARD, NEON_CYAN, NEON_CYAN_DIM } from "@/constants/neon";

export const CYAN = NEON_CYAN;
export const CYAN_DIM = NEON_CYAN_DIM;

export const SECTION_CARD_STYLE = {
  background: BG_CARD,
  border: "1px solid rgba(255,255,255,0.06)",
  borderRadius: "8px",
  padding: "24px",
} as const;

/** Why a cover panel photo upload failed: the file itself, a rate limit, the network or the server. */
export const UPLOAD_FAILURE = {
  INVALID: "invalid",
  RATE_LIMITED: "rateLimited",
  NETWORK: "network",
  SERVER: "server",
} as const;
