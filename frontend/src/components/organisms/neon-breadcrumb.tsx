import Link from "next/link";
import { useTranslations } from "next-intl";
import { TEXT_DIM, TEXT_MUTED } from "@/constants/neon";

const BREADCRUMB_LINK_CLASS =
  "rounded no-underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-bg-deep";

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

export interface NeonBreadcrumbProps {
  items: BreadcrumbItem[];
}

/**
 * Mono breadcrumb trail. Items that carry an `href` render as links (so every
 * page that passes one gets a working back link); the current, last item is
 * plain text.
 */
export function NeonBreadcrumb({
  items,
}: Readonly<NeonBreadcrumbProps>): React.ReactElement {
  const t = useTranslations("common");
  return (
    <nav aria-label={t("breadcrumbNavLabel")}>
      <ol
        className="flex flex-wrap items-center gap-1"
        style={{
          fontFamily: "'JetBrains Mono', ui-monospace, monospace",
          fontSize: "11px",
          color: TEXT_DIM,
          listStyle: "none",
          margin: 0,
          padding: 0,
        }}
      >
        {items.map((item, index) => {
          const isCurrent = index === items.length - 1;
          return (
            <li
              key={`${item.label}-${index}`}
              aria-current={isCurrent ? "page" : undefined}
              style={{
                color: isCurrent ? TEXT_MUTED : TEXT_DIM,
              }}
            >
              {index > 0 && <span aria-hidden="true">{" / "}</span>}
              {item.href !== undefined && !isCurrent ? (
                <Link
                  href={item.href}
                  className={BREADCRUMB_LINK_CLASS}
                  style={{ color: TEXT_DIM }}
                >
                  {item.label}
                </Link>
              ) : (
                item.label
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
