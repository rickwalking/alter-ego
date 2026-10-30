"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";

const THEME_LINK_CLASS =
  "rounded underline decoration-neon-cyan/40 hover:decoration-neon-cyan focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-bg-deep";

/**
 * The row's theme title: a link to the run's carousel when one exists, plain
 * text otherwise (backlog themes have no carousel yet).
 */
export function QueueThemeTitle({
  theme,
  projectId,
}: Readonly<{ theme: string; projectId: string | null }>): React.ReactElement {
  const t = useTranslations("workflow.queue");
  if (projectId === null) return <>{theme}</>;
  return (
    <Link
      href={DASHBOARD_ROUTES.CREATE_WORKSPACE(projectId)}
      className={THEME_LINK_CLASS}
      aria-label={t("actionForTheme", { action: t("openCarousel"), theme })}
    >
      {theme}
    </Link>
  );
}
