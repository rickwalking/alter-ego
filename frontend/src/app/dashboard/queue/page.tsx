"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonTopBar } from "@/components/organisms/neon-top-bar";
import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";
import { DASHBOARD_PAGE_FONT_FAMILY } from "@/constants/dashboard-page";
import { QueuePanelSection } from "./queue-panel-section";

/** The generation queue on its own admin page, linked from the board. */
export default function GenerationQueuePage(): React.ReactElement {
  const t = useTranslations("workflow.queue");
  return (
    <div
      className="flex-1 text-white relative"
      style={{ fontFamily: DASHBOARD_PAGE_FONT_FAMILY }}
    >
      <NeonTopBar
        title={t("title")}
        breadcrumb={[{ label: t("title") }]}
        actions={
          <Link href={DASHBOARD_ROUTES.WORKFLOW}>
            <NeonButton size="sm" variant="secondary">
              {t("boardLink")}
            </NeonButton>
          </Link>
        }
      />
      <div className="mx-auto max-w-[960px] p-6">
        <QueuePanelSection />
      </div>
    </div>
  );
}
