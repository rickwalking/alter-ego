"use client";

import { useTranslations } from "next-intl";
import {
  CALENDAR_COLORS,
  CALENDAR_FLEX_CENTER,
  CALENDAR_LEGEND,
} from "@/modules/editorial-operations";

export function CalendarLegend(): React.ReactElement {
  const t = useTranslations("workflow.calendar.legend");
  return (
    <div style={{ display: "flex", gap: 16, marginTop: 16, flexWrap: "wrap" }}>
      {CALENDAR_LEGEND.map((item) => (
        <div
          key={item.key}
          style={{
            ...CALENDAR_FLEX_CENTER,
            gap: 6,
            fontSize: 11,
            color: CALENDAR_COLORS.tD,
            cursor: "pointer",
          }}
        >
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: item.c,
              flexShrink: 0,
            }}
          />
          {t(item.key)}
        </div>
      ))}
    </div>
  );
}
