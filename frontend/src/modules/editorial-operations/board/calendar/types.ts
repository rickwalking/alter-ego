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

export interface CalendarEvent {
  title: string;
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
