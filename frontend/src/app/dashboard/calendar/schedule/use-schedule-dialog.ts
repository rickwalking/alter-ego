"use client";

import { useCallback, useMemo, useState } from "react";
import type { BlogPost } from "@/modules/publishing";
import {
  minScheduleTime,
  parseScheduleTime,
  validateSchedule,
} from "./schedule-helpers";
import { requestSchedule } from "./schedule-request";
import { useSchedulablePosts } from "./use-schedulable-posts";
import { useScheduleConflicts } from "./use-schedule-conflicts";
import type {
  ScheduleDraft,
  ScheduleRequestError,
  ScheduleValidationError,
  UseScheduleDialogResult,
} from "./types";

const EMPTY_DRAFT: ScheduleDraft = { postId: "", time: "" };

type ScheduleError = ScheduleValidationError | ScheduleRequestError;

/**
 * State of the Schedule Post dialog: the approved posts and the unapproved ones
 * (loaded when the dialog opens), the chosen post and local time, the calendar
 * items within an hour of it (a warning, not a block) and the submit, which
 * validates first and then POSTs to the existing schedule endpoint.
 */
export function useScheduleDialog(
  onScheduled: (post: BlogPost) => void,
): UseScheduleDialogResult {
  const list = useSchedulablePosts();
  const [draft, setDraft] = useState<ScheduleDraft>(EMPTY_DRAFT);
  const [error, setError] = useState<ScheduleError | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const minTime = useMemo(() => minScheduleTime(new Date()), []);
  const conflicts = useScheduleConflicts(draft);

  const submit = useCallback(async () => {
    const invalid = validateSchedule(draft, new Date());
    const post = list.posts.find((candidate) => candidate.id === draft.postId);
    const at = parseScheduleTime(draft.time);
    if (invalid || !post || !at) {
      setError(invalid ?? "postRequired");
      return;
    }
    setSubmitting(true);
    setError(null);
    const result = await requestSchedule(post, at);
    setSubmitting(false);
    if (!result.ok) {
      setError(result.error);
      return;
    }
    onScheduled(result.post);
  }, [draft, list.posts, onScheduled]);

  const changeDraft = useCallback((next: ScheduleDraft) => {
    setDraft(next);
    setError(null);
  }, []);

  return {
    ...list,
    draft,
    setDraft: changeDraft,
    minTime,
    conflicts,
    error,
    submitting,
    submit,
  };
}
