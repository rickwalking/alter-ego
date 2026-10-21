"use client";

import { useEffect, useRef, useState } from "react";
import type { BlogPostFilters } from "@/modules/publishing";
import {
  BLOG_POSTS_SEARCH_DEBOUNCE_MS,
  blogPostsPageFilters,
} from "@/app/dashboard/blog-posts/blog-posts-paging";
import type {
  BlogPostListQuery,
  UseBlogPostsPagingResult,
} from "@/app/dashboard/blog-posts/types";

export const INITIAL_BLOG_POST_LIST_QUERY: BlogPostListQuery = {
  page: 0,
  status: "",
  search: "",
};

/**
 * Page, status and search of the dashboard blog list. Every change
 * sends new limit/offset/status/search filters to the API; a new status or
 * search goes back to the first page. Search waits for a pause in typing.
 *
 * A ref holds the latest query so a debounced search never applies a stale
 * status.
 */
export function useBlogPostsPaging(
  setFilters: (filters: BlogPostFilters) => void,
): UseBlogPostsPagingResult {
  const [query, setQuery] = useState(INITIAL_BLOG_POST_LIST_QUERY);
  const [searchInput, setSearchInput] = useState("");
  const queryRef = useRef(INITIAL_BLOG_POST_LIST_QUERY);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(
    () => () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    },
    [],
  );

  const apply = (change: Partial<BlogPostListQuery>): void => {
    const next = { ...queryRef.current, ...change };
    queryRef.current = next;
    setQuery(next);
    setFilters(blogPostsPageFilters(next));
  };

  const changeSearch = (value: string): void => {
    setSearchInput(value);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(
      () => apply({ search: value, page: 0 }),
      BLOG_POSTS_SEARCH_DEBOUNCE_MS,
    );
  };

  return {
    page: query.page,
    statusFilter: query.status,
    searchInput,
    goToPage: (page) => apply({ page }),
    changeStatus: (status) => apply({ status, page: 0 }),
    changeSearch,
  };
}
