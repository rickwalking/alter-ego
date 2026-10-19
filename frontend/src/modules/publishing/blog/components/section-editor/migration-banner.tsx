"use client";

import { useTranslations } from "next-intl";
import {
  NeonAlert,
  NeonAlertDescription,
  NeonAlertTitle,
} from "@/components/molecules/neon-alert";
import { BLOG_EDITOR_I18N_NAMESPACE } from "@/constants/blog-editor";
import type { MigrationBannerProps } from "./types";

/**
 * Blocking "migration pending" banner (AE-0424 AC15): the stored row is still
 * legacy markdown, so content writes are refused by the API. The editor shows
 * the API error and never parses or persists the legacy shape itself.
 */
export function MigrationBanner({
  detail,
}: MigrationBannerProps): React.ReactElement {
  const t = useTranslations(BLOG_EDITOR_I18N_NAMESPACE);
  return (
    <NeonAlert
      variant="destructive"
      role="alert"
      data-testid="migration-pending-banner"
    >
      <NeonAlertTitle>{t("migration.title")}</NeonAlertTitle>
      <NeonAlertDescription>
        {t("migration.body")}
        {detail && <code className="ml-1">{detail}</code>}
      </NeonAlertDescription>
    </NeonAlert>
  );
}
