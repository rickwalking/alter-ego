import { describe, it, expect } from "vitest";
import { mapCalendarEventToCardProps } from "@/modules/editorial-operations/board/calendar/adapters/calendar-adapter";

describe("mapCalendarEventToCardProps", () => {
  it("maps carousel content type to cyan accent", () => {
    const result = mapCalendarEventToCardProps({
      id: "1",
      title: "Post",
      status: "scheduled",
      contentType: "carousel",
    });
    expect(result.accent).toBe("cyan");
    expect(result.badgeVariant).toBe("cyan");
  });

  it("falls back when content type is unknown", () => {
    const result = mapCalendarEventToCardProps({
      id: "2",
      title: "Post",
      status: "unknown",
      contentType: "other",
    });
    expect(result.accent).toBe("none");
    expect(result.badgeVariant).toBe("cyan");
  });
});
