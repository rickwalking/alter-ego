import { z } from "zod";

export const neonProgressBarPropsSchema = z.object({
  value: z.number().min(0).max(100),
  max: z.number().positive().default(100),
  label: z.string().optional(),
});

export type NeonProgressBarProps = z.infer<typeof neonProgressBarPropsSchema>;
