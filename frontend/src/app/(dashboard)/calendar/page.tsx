"use client";

import { useTranslations } from "next-intl";
import { ContentCalendarView } from "@/features/workflow/components/content-calendar-view";

export default function ContentCalendarPage() {
  const t = useTranslations("workflow.calendar");

  return (
    <div className="container mx-auto py-8 px-4">
      <h1 className="text-2xl font-bold mb-6">{t("title")}</h1>
      <p className="text-muted-foreground mb-6">{t("subtitle")}</p>
      <ContentCalendarView />
    </div>
  );
}
