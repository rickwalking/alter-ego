import { type ReactNode } from "react";
import { NeonBreadcrumb, type BreadcrumbItem } from "@/components/organisms/neon-breadcrumb";
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
      style={{
        height: "56px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 32px",
        borderBottom: `1px solid ${NEON_BORDER_SUBTLE}`,
        background: NEON_BG_HEADER,
        backdropFilter: "blur(12px)",
        position: "sticky",
        top: 0,
        zIndex: 30,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <h1
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
          <NeonBreadcrumb items={breadcrumb} />
        )}
      </div>
      {actions && <div>{actions}</div>}
    </div>
  );
}
