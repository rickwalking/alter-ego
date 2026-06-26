import { z } from "zod";
import {
  NEON_AMBER,
  NEON_AMBER_BADGE_BG,
  NEON_CYAN,
  NEON_CYAN_BADGE_BG,
  NEON_GREEN,
  NEON_GREEN_BADGE_BG,
  NEON_MAGENTA,
  NEON_MAGENTA_BADGE_BG,
  NEON_RED,
  NEON_RED_BADGE_BG,
  NEON_TEAL,
  NEON_TEAL_BADGE_BG,
} from "@/constants/neon";

export const neonBadgeVariantSchema = z.enum([
  "cyan",
  "magenta",
  "teal",
  "amber",
  "green",
  "red",
]);
export const neonBadgeSizeSchema = z.enum(["sm", "md"]);

export const neonBadgePropsSchema = z.object({
  variant: neonBadgeVariantSchema.default("cyan"),
  size: neonBadgeSizeSchema.default("md"),
  dot: z.boolean().default(false),
  pulse: z.boolean().default(false),
  outline: z.boolean().default(false),
});

export type NeonBadgeVariant = z.infer<typeof neonBadgeVariantSchema>;
export type NeonBadgeSize = z.infer<typeof neonBadgeSizeSchema>;

export const BADGE_COLORS: Record<
  NeonBadgeVariant,
  { bg: string; text: string }
> = {
  cyan: { bg: NEON_CYAN_BADGE_BG, text: NEON_CYAN },
  magenta: { bg: NEON_MAGENTA_BADGE_BG, text: NEON_MAGENTA },
  teal: { bg: NEON_TEAL_BADGE_BG, text: NEON_TEAL },
  amber: { bg: NEON_AMBER_BADGE_BG, text: NEON_AMBER },
  green: { bg: NEON_GREEN_BADGE_BG, text: NEON_GREEN },
  red: { bg: NEON_RED_BADGE_BG, text: NEON_RED },
};
