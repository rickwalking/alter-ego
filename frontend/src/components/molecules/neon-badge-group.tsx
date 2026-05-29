import { type ReactNode } from "react";
import { NeonBadge, type NeonBadgeProps } from "@/components/atoms/neon-badge";

export interface NeonBadgeGroupItem {
  label: string;
  variant?: NeonBadgeProps["variant"];
}

export interface NeonBadgeGroupProps {
  items: NeonBadgeGroupItem[];
  className?: string;
  children?: ReactNode;
}

export function NeonBadgeGroup({
  items,
  className,
  children,
}: NeonBadgeGroupProps): React.ReactElement {
  return (
    <div className={`flex flex-wrap gap-2 ${className ?? ""}`}>
      {items.map((item) => (
        <NeonBadge key={item.label} variant={item.variant ?? "cyan"}>
          {item.label}
        </NeonBadge>
      ))}
      {children}
    </div>
  );
}
