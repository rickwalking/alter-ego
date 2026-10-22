"use client";

import { useTranslations } from "next-intl";
import { NeonInput } from "@/components/atoms/neon-input";
import { NeonLabel } from "@/components/atoms/neon-label";
import { NeonSelect } from "@/components/atoms/neon-select";
import { NeonAlert } from "@/components/molecules/neon-alert";
import { resolveDisplayTitle } from "@/lib/public-blog-text";
import {
  SCHEDULE_POST_FIELD_ID,
  SCHEDULE_TIME_FIELD_ID,
  SCHEDULE_TIME_HINT_ID,
} from "./constants";
import { viewerTimeZone } from "./schedule-helpers";
import type { ScheduleFormProps } from "./types";

/**
 * Post picker (approved posts, then drafts and posts under review disabled
 * with "approve it first"), local date-time field (with the viewer's
 * timezone) and the calendar items within an hour of the chosen time.
 */
export function ScheduleForm({
  posts,
  unapproved,
  draft,
  onDraftChange,
  minTime,
  conflicts,
}: Readonly<ScheduleFormProps>): React.ReactElement {
  const t = useTranslations("workflow.calendar.schedule");
  const titleOf = (title: string): string =>
    resolveDisplayTitle([title]) || t("untitled");
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-2">
        <NeonLabel htmlFor={SCHEDULE_POST_FIELD_ID}>{t("post")}</NeonLabel>
        <NeonSelect
          id={SCHEDULE_POST_FIELD_ID}
          value={draft.postId}
          onChange={(e) => onDraftChange({ ...draft, postId: e.target.value })}
        >
          <option value="">{t("choosePost")}</option>
          {posts.map((post) => (
            <option key={post.id} value={post.id}>
              {titleOf(post.title)}
            </option>
          ))}
          {unapproved.map((post) => (
            <option key={post.id} value={post.id} disabled>
              {t("approveFirst", { title: titleOf(post.title) })}
            </option>
          ))}
        </NeonSelect>
      </div>
      <div className="flex flex-col gap-2">
        <NeonLabel htmlFor={SCHEDULE_TIME_FIELD_ID}>{t("time")}</NeonLabel>
        <NeonInput
          id={SCHEDULE_TIME_FIELD_ID}
          type="datetime-local"
          min={minTime}
          value={draft.time}
          aria-describedby={SCHEDULE_TIME_HINT_ID}
          onChange={(e) => onDraftChange({ ...draft, time: e.target.value })}
        />
        <p id={SCHEDULE_TIME_HINT_ID} className="text-xs opacity-70">
          {t("timezone", { zone: viewerTimeZone() })}
        </p>
      </div>
      {conflicts.length > 0 && (
        <NeonAlert role="status">
          {t("conflict", {
            titles: conflicts.map((item) => titleOf(item.title)).join(", "),
          })}
        </NeonAlert>
      )}
    </div>
  );
}
