import { z } from "zod";

export const sidebarItemSchema = z.object({
  href: z.string(),
  labelKey: z.string(),
  icon: z.string(),
  badge: z.string().optional(),
});

export const sidebarSectionSchema = z.object({
  sectionKey: z.string(),
  items: z.array(sidebarItemSchema).min(1),
});

export const neonSidebarPropsSchema = z.object({
  sections: z.array(sidebarSectionSchema).min(1),
});

export type SidebarItem = z.infer<typeof sidebarItemSchema>;
export type SidebarSection = z.infer<typeof sidebarSectionSchema>;
