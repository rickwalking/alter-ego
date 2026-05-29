import { z } from "zod";

export const neonButtonVariantSchema = z.enum([
  "primary",
  "secondary",
  "ghost",
  "danger",
]);
export const neonButtonSizeSchema = z.enum(["sm", "md", "lg"]);

export const neonButtonPropsSchema = z.object({
  variant: neonButtonVariantSchema.default("primary"),
  size: neonButtonSizeSchema.default("md"),
  disabled: z.boolean().default(false),
  loading: z.boolean().default(false),
  fullWidth: z.boolean().default(false),
  type: z.enum(["button", "submit", "reset"]).default("button"),
});

export type NeonButtonVariant = z.infer<typeof neonButtonVariantSchema>;
export type NeonButtonSize = z.infer<typeof neonButtonSizeSchema>;
export type NeonButtonProps = z.infer<typeof neonButtonPropsSchema>;

export const NEON_BUTTON_DEFAULTS = {
  variant: "primary" as const,
  size: "md" as const,
  disabled: false,
  loading: false,
  fullWidth: false,
  type: "button" as const,
} as const;
