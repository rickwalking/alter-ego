export type CalendarContentType =
  | "carousel"
  | "blog"
  | "meeting"
  | "management";

export type CalendarStatusType =
  | "published"
  | "approved"
  | "in_progress"
  | "awaiting_human";

export type CalendarView = "month" | "week" | "day";

/** What a calendar view shows: its kind, the focused day and the local today. */
export interface CalendarViewTarget {
  view: CalendarView;
  focus: Date;
  /** The viewer's local day; null (not yet known) highlights no cell. */
  today: Date | null;
}

/** Inclusive local-date span a calendar view shows. */
export interface CalendarRange {
  start: Date;
  end: Date;
}

export interface CalendarEvent {
  id: string;
  title: string;
  /** The item's instant (ISO) when it has a time of day; absent for date-only items. */
  at?: string;
  contentType: CalendarContentType;
  status?: CalendarStatusType;
}

export interface CalendarDay {
  day: number;
  /** The cell's real calendar date as `yyyy-MM-dd` (for labels + event match). */
  iso: string;
  cur: boolean;
  today: boolean;
  events: CalendarEvent[];
}

export type CalendarIconName =
  | "left"
  | "right"
  | "plus"
  | "sync"
  | "grid"
  | "file"
  | "cal"
  | "user";
