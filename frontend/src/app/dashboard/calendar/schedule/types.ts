import type { CalendarItem } from "@/modules/editorial";
import type { BlogPost } from "@/modules/publishing";

/** Why a chosen time cannot be scheduled (an i18n key under `errors`). */
export type ScheduleValidationError =
  | "postRequired"
  | "timeRequired"
  | "timeInPast";

/** Why the backend refused the schedule (an i18n key under `errors`). */
export type ScheduleRequestError =
  | "timeInPast"
  | "versionConflict"
  | "notReady"
  | "failed";

export type ScheduleRequestResult =
  | { ok: true; post: BlogPost }
  | { ok: false; error: ScheduleRequestError };

export interface ScheduleDraft {
  postId: string;
  /** The `datetime-local` value, a local wall-clock time. */
  time: string;
}

export interface ScheduleDialogProps {
  open: boolean;
  onClose: () => void;
  /** Called with the scheduled post after the backend accepted it. */
  onScheduled: (post: BlogPost) => void;
}

export interface ScheduleFormProps {
  posts: BlogPost[];
  /** Drafts and posts under review: listed, but not selectable. */
  unapproved: BlogPost[];
  draft: ScheduleDraft;
  onDraftChange: (draft: ScheduleDraft) => void;
  /** Earliest selectable `datetime-local` value. */
  minTime: string;
  conflicts: CalendarItem[];
}

export interface SchedulablePosts {
  posts: BlogPost[];
  unapproved: BlogPost[];
  loading: boolean;
  loadError: string | null;
}

export interface UseScheduleDialogResult extends SchedulablePosts {
  draft: ScheduleDraft;
  setDraft: (draft: ScheduleDraft) => void;
  minTime: string;
  conflicts: CalendarItem[];
  error: ScheduleValidationError | ScheduleRequestError | null;
  submitting: boolean;
  submit: () => Promise<void>;
}

export interface ScheduleDialogBodyProps {
  state: UseScheduleDialogResult;
}

export interface UseScheduleFlowResult {
  open: boolean;
  /** Confirmation of the last schedule, shown above the calendar. */
  notice: string | null;
  openDialog: () => void;
  close: () => void;
  onScheduled: (post: BlogPost) => void;
}
