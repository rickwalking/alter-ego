import { z } from "zod";
import {
  NEON_AMBER,
  NEON_CYAN,
  NEON_MAGENTA,
  NEON_PURPLE,
  NEON_TEAL,
} from "@/constants/neon";

export const neonCardAccentSchema = z.enum([
  "cyan",
  "magenta",
  "teal",
  "amber",
  "purple",
  "none",
]);
export const neonCardPaddingSchema = z.enum(["sm", "md", "lg"]);

export const neonCardPropsSchema = z.object({
  accent: neonCardAccentSchema.default("none"),
  hover: z.boolean().default(false),
  padding: neonCardPaddingSchema.default("md"),
  onClick: z.function().args().returns(z.void()).optional(),
});

export type NeonCardAccent = z.infer<typeof neonCardAccentSchema>;
export type NeonCardPadding = z.infer<typeof neonCardPaddingSchema>;

export const CARD_PADDING_MAP: Record<NeonCardPadding, string> = {
  sm: "p-4",
  md: "p-6",
  lg: "p-8",
};

export const CARD_ACCENT_COLORS: Record<
  Exclude<NeonCardAccent, "none">,
  string
> = {
  cyan: NEON_CYAN,
  magenta: NEON_MAGENTA,
  teal: NEON_TEAL,
  amber: NEON_AMBER,
  purple: NEON_PURPLE,
};
