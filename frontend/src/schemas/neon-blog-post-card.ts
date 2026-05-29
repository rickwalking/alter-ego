import { z } from "zod";

export const neonBlogPostCardPropsSchema = z.object({
  id: z.string(),
  title: z.string().min(1),
  subtitle: z.string().optional(),
  niche: z.string().optional(),
  imageUrl: z.string().optional(),
  createdAt: z.string(),
  href: z.string(),
});

export type NeonBlogPostCardProps = z.infer<typeof neonBlogPostCardPropsSchema>;
