import { TEXT_DIM, TEXT_MUTED } from "@/constants/neon";

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

export interface NeonBreadcrumbProps {
  items: BreadcrumbItem[];
}

export function NeonBreadcrumb({ items }: NeonBreadcrumbProps): React.ReactElement {
  return (
    <div
      style={{
        fontFamily: "'JetBrains Mono', ui-monospace, monospace",
        fontSize: "11px",
        color: TEXT_DIM,
      }}
    >
      {items.map((item, index) => (
        <span key={`${item.label}-${index}`}>
          {index > 0 && " / "}
          <span style={{ color: index === items.length - 1 ? TEXT_MUTED : TEXT_DIM }}>
            {item.label}
          </span>
        </span>
      ))}
    </div>
  );
}
