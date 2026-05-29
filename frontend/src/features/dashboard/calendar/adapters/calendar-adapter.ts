import type { NeonCardAccent } from "@/schemas/neon-card";
import type { NeonBadgeVariant } from "@/schemas/neon-badge";

export interface CalendarEventSource {
  id: string;
  title: string;
  status: string;
  contentType: string;
}

export function mapCalendarEventToCardProps(event: CalendarEventSource): {
  accent: NeonCardAccent;
  badgeVariant: NeonBadgeVariant;
  badgeText: string;
} {
  const accentMap: Record<string, NeonCardAccent> = {
    carousel: "cyan",
    blog: "magenta",
    social: "teal",
  };

  const badgeMap: Record<string, NeonBadgeVariant> = {
    scheduled: "cyan",
    published: "green",
    draft: "amber",
    cancelled: "red",
  };

  return {
    accent: accentMap[event.contentType] ?? "none",
    badgeVariant: badgeMap[event.status] ?? "cyan",
    badgeText: event.status,
  };
}
