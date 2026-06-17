import type { CalendarContentType } from "@/modules/editorial-operations";

export const CONTENT_TYPE_ICON: Record<
  CalendarContentType,
  "grid" | "file" | "cal" | "user"
> = {
  carousel: "grid",
  blog: "file",
  meeting: "cal",
  management: "user",
};
