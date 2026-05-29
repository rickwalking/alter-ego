import { z } from "zod";

export const statCardTrendSchema = z.enum(["up", "down"]);

export const neonStatCardPropsSchema = z.object({
  label: z.string().min(1),
  value: z.union([z.string(), z.number()]),
  change: z
    .object({
      value: z.string(),
      trend: statCardTrendSchema,
    })
    .optional(),
  loading: z.boolean().default(false),
});

export type StatCardTrend = z.infer<typeof statCardTrendSchema>;
export type NeonStatCardProps = z.infer<typeof neonStatCardPropsSchema>;
