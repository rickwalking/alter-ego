import type { Document } from "@/schemas/knowledge";
import type { NeonBadgeVariant } from "@/schemas/neon-badge";
import type { NeonCardAccent } from "@/schemas/neon-card";

const STATUS_BADGE_MAP: Record<string, NeonBadgeVariant> = {
  completed: "green",
  processing: "amber",
  pending: "cyan",
  failed: "red",
};

export function mapDocumentToCardProps(doc: Document): {
  accent: NeonCardAccent;
  badgeVariant: NeonBadgeVariant;
  badgeText: string;
} {
  return {
    accent: "cyan",
    badgeVariant: STATUS_BADGE_MAP[doc.status] ?? "amber",
    badgeText: doc.status,
  };
}
