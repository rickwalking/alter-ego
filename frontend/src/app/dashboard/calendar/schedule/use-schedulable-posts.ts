"use client";

import { useMemo } from "react";
import { useBlogPosts } from "@/modules/publishing";
import {
  SCHEDULABLE_PAGE_LIMIT,
  SCHEDULABLE_STATUS,
  UNAPPROVED_STATUSES,
} from "./constants";
import type { SchedulablePosts } from "./types";

/**
 * The posts the dialog lists: one page of approved posts (selectable) and one
 * page of the rest, filtered to drafts and posts under review (shown disabled).
 */
export function useSchedulablePosts(): SchedulablePosts {
  const approved = useBlogPosts({
    status: SCHEDULABLE_STATUS,
    limit: SCHEDULABLE_PAGE_LIMIT,
  });
  const all = useBlogPosts({ limit: SCHEDULABLE_PAGE_LIMIT });
  const unapproved = useMemo(
    () => all.posts.filter((post) => UNAPPROVED_STATUSES.includes(post.status)),
    [all.posts],
  );
  return {
    posts: approved.posts,
    unapproved,
    loading: approved.loading || all.loading,
    loadError: approved.error ?? all.error,
  };
}
