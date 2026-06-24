import { type ReactNode } from "react";
import {
  NeonBreadcrumb,
  type BreadcrumbItem,
} from "@/components/organisms/neon-breadcrumb";
import { NEON_BG_HEADER, NEON_BORDER_SUBTLE, TEXT } from "@/constants/neon";

export interface NeonTopBarProps {
  title: string;
  breadcrumb?: BreadcrumbItem[];
  actions?: ReactNode;
}

export function NeonTopBar({
  title,
  breadcrumb,
  actions,
}: NeonTopBarProps): React.ReactElement {
  return (
    <div
      // Layout via Tailwind so it can respond; neon surface styling stays inline.
      // `pl-14` clears the layout-level mobile hamburger (z-50); `lg:pl-8` restores
      // desktop padding once the rail (and no hamburger) takes over.
      className="sticky top-0 z-50 flex h-14 items-center justify-between gap-3 px-4 pl-14 md:px-8 lg:pl-8"
      style={{
        borderBottom: `1px solid ${NEON_BORDER_SUBTLE}`,
        background: NEON_BG_HEADER,
        backdropFilter: "blur(12px)",
      }}
    >
      <div className="flex min-w-0 items-center gap-3">
        <h1
          className="min-w-0 truncate"
          style={{
            fontSize: "16px",
            fontWeight: 700,
            color: TEXT,
            letterSpacing: "-0.02em",
          }}
        >
          {title}
        </h1>
        {breadcrumb && breadcrumb.length > 0 && (
          <div className="hidden sm:flex">
            <NeonBreadcrumb items={breadcrumb} />
          </div>
        )}
      </div>
      {actions && (
        <div className="flex flex-wrap justify-end gap-2">{actions}</div>
      )}
    </div>
  );
}
