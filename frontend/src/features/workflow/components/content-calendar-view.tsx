"use client";

import { useTranslations } from "next-intl";
import { NeonBadge } from "@/components/atoms/neon-badge";
import { NeonCard, NeonCardContent, NeonCardHeader, NeonCardTitle } from "@/components/molecules/neon-card";
import { NeonSpinner } from "@/components/atoms/neon-spinner";
import { useContentCalendar } from "@/features/workflow/hooks/use-content-calendar";
import { format, parseISO } from "date-fns";

export function ContentCalendarView() {
  const t = useTranslations("workflow.calendar");
  const { calendar, loading, error } = useContentCalendar();

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <NeonSpinner />
      </div>
    );
  }

  if (error) {
    return <p className="text-red-500 text-center py-8">{error}</p>;
  }

  if (!calendar) {
    return null;
  }

  const grouped = calendar.items.reduce<Record<string, typeof calendar.items>>(
    (acc, item) => {
      const day = format(parseISO(item.event_date), "yyyy-MM-dd");
      if (!acc[day]) acc[day] = [];
      acc[day].push(item);
      return acc;
    },
    {},
  );

  const days = Object.keys(grouped).sort();

  return (
    <div className="space-y-4">
      {days.length === 0 && (
        <p className="text-muted-foreground text-center py-8">{t("empty")}</p>
      )}
      {days.map((day) => (
        <NeonCard key={day}>
          <NeonCardHeader className="pb-2">
            <NeonCardTitle className="text-base">
              {format(parseISO(day), "MMMM d, yyyy")}
            </NeonCardTitle>
          </NeonCardHeader>
          <NeonCardContent className="space-y-2">
            {grouped[day]?.map((item) => (
              <div
                key={`${item.content_type}-${item.id}`}
                className="flex items-center justify-between rounded-md border px-3 py-2"
              >
                <div>
                  <p className="font-medium text-sm">{item.title}</p>
                  <p className="text-xs text-muted-foreground">
                    {item.content_type}
                  </p>
                </div>
                <div className="flex gap-2">
                  <NeonBadge variant="outline">{item.status}</NeonBadge>
                  {item.is_scheduled && <NeonBadge>{t("scheduled")}</NeonBadge>}
                </div>
              </div>
            ))}
          </NeonCardContent>
        </NeonCard>
      ))}
    </div>
  );
}
