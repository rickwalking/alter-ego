/** Only approved posts can be scheduled (the backend refuses any other status). */
export const SCHEDULABLE_STATUS = "approved";

/** Statuses listed as disabled options with an "approve it first" note. */
export const UNAPPROVED_STATUSES: readonly string[] = ["draft", "under_review"];

/** The backend's list page cap; the dialog loads one page of each list. */
export const SCHEDULABLE_PAGE_LIMIT = 100;

/** The backend's minimum lead time (`MIN_SCHEDULE_LEAD_SECONDS`). */
export const MIN_SCHEDULE_LEAD_MS = 60_000;

/** Another calendar item within this distance (inclusive) of the chosen time is a conflict. */
export const SCHEDULE_CONFLICT_WINDOW_MS = 60 * 60_000;

/** `datetime-local` value format (local wall-clock time, minute precision). */
export const DATETIME_LOCAL_FORMAT = "yyyy-MM-dd'T'HH:mm";

/** Backend error codes the dialog explains. */
export const SCHEDULE_ERROR_CODE_IN_PAST = "schedule_in_past";

/** Ids that tie the dialog's labels to its fields. */
export const SCHEDULE_POST_FIELD_ID = "schedule-post-id";
export const SCHEDULE_TIME_FIELD_ID = "schedule-post-time";
export const SCHEDULE_TIME_HINT_ID = "schedule-post-time-hint";

export const CONTENT_TYPE_HEADER = "Content-Type";
