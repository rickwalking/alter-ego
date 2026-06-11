"use client";

import * as LucideIcons from "lucide-react";

export interface PresentationIconPreviewProps {
  iconName: string;
  className?: string;
}

function toLucideComponentName(iconName: string): string {
  return iconName
    .split("-")
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join("");
}

export function PresentationIconPreview({
  iconName,
  className,
}: PresentationIconPreviewProps): React.ReactElement {
  const componentName = toLucideComponentName(iconName);
  const Icon = LucideIcons[componentName as keyof typeof LucideIcons] as
    | LucideIcons.LucideIcon
    | undefined;

  if (!Icon) {
    return (
      <span className={className} data-testid="presentation-icon-fallback">
        {iconName}
      </span>
    );
  }

  return (
    <Icon className={className} aria-hidden data-testid="presentation-icon" />
  );
}
