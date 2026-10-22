/**
 * Scenarios: tests/features/calendar-schedule-post.feature.
 */
import { afterEach, describe, expect, it } from "vitest";
import type { CalendarItem } from "@/modules/editorial";
import {
  conflictWindow,
  findScheduleConflicts,
  minScheduleTime,
  parseScheduleTime,
  validateSchedule,
  viewerTimeZone,
} from "./schedule-helpers";

const ORIGINAL_TZ = process.env.TZ;

function restoreTimeZone(): void {
  if (ORIGINAL_TZ === undefined) {
    delete process.env.TZ;
  } else {
    process.env.TZ = ORIGINAL_TZ;
  }
}
const NOW = new Date(2026, 9, 22, 10, 0, 0);

afterEach(() => {
  restoreTimeZone();
});

describe("schedule helpers", () => {
  // Scenario: The time is entered in the viewer's timezone
  it("names the viewer's timezone and starts one minute from now", () => {
    process.env.TZ = "America/Sao_Paulo";
    expect(viewerTimeZone()).toBe("America/Sao_Paulo");
    expect(minScheduleTime(new Date(2026, 9, 22, 10, 0))).toBe(
      "2026-10-22T10:01",
    );
  });

  it("reads a datetime-local value as local time", () => {
    process.env.TZ = "America/Sao_Paulo";
    expect(parseScheduleTime("2026-10-23T20:00")?.toISOString()).toBe(
      "2026-10-23T23:00:00.000Z",
    );
    expect(parseScheduleTime("")).toBeNull();
    expect(parseScheduleTime("tomorrow")).toBeNull();
  });

  // Scenario: A post and a time are required
  it("requires a post, then a time", () => {
    expect(
      validateSchedule({ postId: "", time: "2026-10-23T20:00" }, NOW),
    ).toBe("postRequired");
    expect(validateSchedule({ postId: "a", time: "" }, NOW)).toBe(
      "timeRequired",
    );
  });

  // Scenario: A time in the past is refused before sending
  it("refuses a time less than a minute ahead and accepts one after it", () => {
    expect(
      validateSchedule({ postId: "a", time: "2026-10-22T09:00" }, NOW),
    ).toBe("timeInPast");
    expect(
      validateSchedule({ postId: "a", time: "2026-10-22T10:00" }, NOW),
    ).toBe("timeInPast");
    expect(
      validateSchedule({ postId: "a", time: "2026-10-22T10:02" }, NOW),
    ).toBeNull();
  });

  // Scenario: Another calendar item within an hour is flagged
  it("flags calendar items within an hour, inclusive", () => {
    const at = new Date("2026-10-23T23:00:00.000Z");
    const item = (id: string, minutes: number): CalendarItem => ({
      id,
      content_type: "blog_post",
      title: id,
      status: "approved",
      event_date: new Date(at.getTime() + minutes * 60_000).toISOString(),
      is_scheduled: true,
    });
    const items = [item("before", -60), item("near", 30), item("far", 61)];
    expect(
      findScheduleConflicts(items, { postId: "self", at }).map((c) => c.id),
    ).toEqual(["before", "near"]);
    expect(conflictWindow(at)).toEqual({
      start: "2026-10-23T22:00:00.000Z",
      end: "2026-10-24T00:00:00.000Z",
    });
  });

  // Scenario: The post being scheduled is not its own conflict
  it("never flags the post being scheduled", () => {
    const at = new Date("2026-10-23T23:00:00.000Z");
    const self: CalendarItem = {
      id: "self",
      content_type: "blog_post",
      title: "Launch",
      status: "approved",
      event_date: "2026-10-23T23:15:00+00:00",
    };
    expect(findScheduleConflicts([self], { postId: "self", at })).toEqual([]);
  });
});
