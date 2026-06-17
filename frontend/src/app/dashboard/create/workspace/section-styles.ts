import { BG_CARD, TEXT } from "@/constants/neon";

/**
 * Shared inline styles for the create-carousel workspace sections (AE-0154).
 * The topic / theme / template section cards used byte-identical style objects;
 * they now import these.
 */

export const sectionCardStyle = {
  background: BG_CARD,
  border: "1px solid rgba(255,255,255,0.06)",
  borderRadius: "8px",
  padding: "24px",
} as const;

export const sectionHeaderStyle = {
  fontSize: "14px",
  fontWeight: 700,
  marginBottom: "12px",
  display: "flex",
  alignItems: "center",
  gap: "8px",
} as const;

export const inputStyle = {
  width: "100%",
  padding: "10px 12px",
  borderRadius: "6px",
  border: "1px solid rgba(255,255,255,0.08)",
  background: "rgba(6,10,18,0.6)",
  color: TEXT,
  fontSize: "13px",
  outline: "none",
} as const;
