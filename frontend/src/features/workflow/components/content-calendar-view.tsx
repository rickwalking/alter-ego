"use client";

import { useTranslations } from "next-intl";
import {
  Badge,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Spinner,
} from "@/components/ui";
import { useContentCalendar } from "@/features/workflow/hooks/use-content-calendar";
import { format, parseISO } from "date-fns";

export function ContentCalendarView() {
  const t = useTranslations("workflow.calendar");
  const { calendar, loading, error } = useContentCalendar();

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner />
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
        <Card key={day}>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">
              {format(parseISO(day), "MMMM d, yyyy")}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
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
                  <Badge variant="outline">{item.status}</Badge>
                  {item.is_scheduled && <Badge>{t("scheduled")}</Badge>}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
