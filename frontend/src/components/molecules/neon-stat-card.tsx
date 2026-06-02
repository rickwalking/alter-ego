import { type ReactNode } from "react";
import { NeonCard } from "@/components/molecules/neon-card";
import { NeonSkeleton } from "@/components/atoms/neon-skeleton";
import {
  NEON_CYAN_DIM,
  NEON_GREEN,
  NEON_RED,
  TEXT,
  TEXT_MUTED,
} from "@/constants/neon";
import type { StatCardTrend } from "@/schemas/neon-stat-card";

export interface NeonStatCardComponentProps {
  label: string;
  value: string | number;
  change?: { value: string; trend: StatCardTrend };
  loading?: boolean;
  icon?: ReactNode;
  iconBg?: string;
}

export function NeonStatCard({
  label,
  value,
  change,
  loading,
  icon,
  iconBg,
}: NeonStatCardComponentProps): React.ReactElement {
  if (loading) {
    return (
      <NeonCard padding="md">
        <NeonSkeleton variant="text" />
        <NeonSkeleton variant="text" className="mt-2 w-1/2" />
      </NeonCard>
    );
  }

  const trendColor = change?.trend === "up" ? NEON_GREEN : NEON_RED;

  return (
    <NeonCard padding="md" hover>
      <div className="flex items-start gap-4">
        {icon && (
          <div
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg"
            style={{ background: iconBg ?? NEON_CYAN_DIM }}
          >
            {icon}
          </div>
        )}
        <div className="flex-1 min-w-0">
          <p className="text-[13px]" style={{ color: TEXT_MUTED }}>
            {label}
          </p>
          <p
            className="text-[28px] font-bold tracking-tight mt-1"
            style={{ color: TEXT }}
          >
            {value}
          </p>
          {change && (
            <span className="text-xs font-medium" style={{ color: trendColor }}>
              {change.value}
            </span>
          )}
        </div>
      </div>
    </NeonCard>
  );
}
