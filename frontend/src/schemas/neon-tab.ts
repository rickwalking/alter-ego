import { z } from "zod";

export const neonTabVariantSchema = z.enum(["default", "pills"]);

export const neonTabPropsSchema = z.object({
  defaultValue: z.string().optional(),
  variant: neonTabVariantSchema.default("default"),
});

export type NeonTabVariant = z.infer<typeof neonTabVariantSchema>;
