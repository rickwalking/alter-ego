import Link from "next/link";

import { NEON_CYAN, TEXT_MUTED } from "@/constants/neon";
import { PUBLIC_ROUTE_PATHS } from "@/constants/public-routes";

/** The public blog with no published article: a visitor message and a way on. */
export function BlogEmptyState({
  message,
  linkLabel,
}: Readonly<{ message: string; linkLabel: string }>): React.ReactElement {
  return (
    <>
      <p style={{ fontSize: "16px", color: TEXT_MUTED }}>{message}</p>
      <Link
        href={PUBLIC_ROUTE_PATHS.CAROUSELS}
        style={{
          display: "inline-block",
          marginTop: "16px",
          fontSize: "14px",
          fontWeight: 600,
          color: NEON_CYAN,
        }}
      >
        {linkLabel}
      </Link>
    </>
  );
}
