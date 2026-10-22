import { z } from "zod";

export const sidebarItemSchema = z.object({
  href: z.string(),
  labelKey: z.string(),
  icon: z.string(),
  badge: z.string().optional(),
  access: z.enum(["admin"]).optional(),
});

export const sidebarSectionSchema = z.object({
  sectionKey: z.string(),
  items: z.array(sidebarItemSchema).min(1),
});

export type SidebarSection = z.infer<typeof sidebarSectionSchema>;
