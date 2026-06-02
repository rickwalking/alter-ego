import { NeonBadge } from "@/components/atoms/neon-badge";
import { NeonCard } from "@/components/molecules/neon-card";
import { TEXT, TEXT_MUTED } from "@/constants/neon";
import type { NeonBadgeVariant } from "@/schemas/neon-badge";

export interface ActivityItem {
  id: string;
  title: string;
  description: string;
  time: string;
  badge?: string;
  badgeVariant?: NeonBadgeVariant;
}

export interface NeonActivityListProps {
  title: string;
  activities: ActivityItem[];
}

export function NeonActivityList({
  title,
  activities,
}: NeonActivityListProps): React.ReactElement {
  return (
    <NeonCard padding="md" className="overflow-hidden">
      <h2
        className="font-extrabold tracking-tight mb-4"
        style={{ fontSize: 18, color: TEXT }}
      >
        {title}
      </h2>
      <div className="space-y-0">
        {activities.map((activity, index) => (
          <div
            key={activity.id}
            className="flex items-start gap-3 py-3"
            style={{
              borderBottom:
                index < activities.length - 1
                  ? "1px solid rgba(255,255,255,0.04)"
                  : undefined,
            }}
          >
            <NeonBadge
              variant={activity.badgeVariant ?? "cyan"}
              dot
              size="sm"
            />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold" style={{ color: TEXT }}>
                {activity.title}
              </p>
              <p className="text-xs mt-0.5" style={{ color: TEXT_MUTED }}>
                {activity.description}
              </p>
            </div>
            <span
              className="text-[10px] shrink-0"
              style={{
                fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                color: TEXT_MUTED,
              }}
            >
              {activity.time}
            </span>
          </div>
        ))}
      </div>
    </NeonCard>
  );
}
