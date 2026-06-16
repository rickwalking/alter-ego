"use client";

import { PresentationIconPreview } from "@/modules/editorial/workspace/components/presentation-icon-preview";
import type { PresentationStructuredItem } from "@/modules/editorial/workspace/lib/presentation-review-utils";

export interface PresentationStructuredItemsProps {
  items: PresentationStructuredItem[];
  className?: string;
}

export function PresentationStructuredItems({
  items,
  className,
}: PresentationStructuredItemsProps): React.ReactElement | null {
  if (items.length === 0) {
    return null;
  }

  return (
    <ul className={className ?? "space-y-2 pt-1"}>
      {items.map((item, index) => {
        const title = typeof item.title === "string" ? item.title.trim() : "";
        const body = typeof item.body === "string" ? item.body.trim() : "";
        const iconName =
          typeof item.icon_name === "string" ? item.icon_name.trim() : "";
        const key = `${iconName}-${title}-${index}`;

        return (
          <li
            key={key}
            className="flex items-start gap-2 rounded-md border border-[var(--color-border)] p-2"
          >
            {iconName ? (
              <PresentationIconPreview
                iconName={iconName}
                className="mt-0.5 h-4 w-4 shrink-0 text-[var(--color-text)]"
              />
            ) : null}
            <div className="min-w-0 space-y-0.5">
              {title ? (
                <p className="font-medium text-[var(--color-text)] text-xs">
                  {title}
                </p>
              ) : null}
              {body ? (
                <p className="whitespace-pre-wrap text-[var(--color-text-muted)] text-xs">
                  {body}
                </p>
              ) : null}
            </div>
          </li>
        );
      })}
    </ul>
  );
}
