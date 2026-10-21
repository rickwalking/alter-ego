import { z } from "zod";

export const statCardTrendSchema = z.enum(["up", "down"]);

export type StatCardTrend = z.infer<typeof statCardTrendSchema>;
