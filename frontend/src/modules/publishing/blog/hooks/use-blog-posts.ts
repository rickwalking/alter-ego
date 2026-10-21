"use client";

/**
 * Custom hook for managing blog posts with search/filter (UI-028).
 */

import { useCallback, useEffect, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import type {
  BlogPost,
  BlogPostCreatePayload,
  BlogPostUpdatePayload,
} from "../types";
import {
  BLOG_POST_ERR_CAROUSEL_DELETE_BLOCKED,
  BLOG_POST_ERR_VERSION_CONFLICT,
  BlogPostMutationError,
} from "../constants";
import {
  createBlogPost,
  deleteBlogPost,
  fetchBlogPostPage,
  postBlogPostAction,
  unpublishBlogPost,
  updateBlogPost,
} from "../blog-post-list-requests";
import type { BlogPostFilters, BlogPostList } from "./types";

/** The paged, filtered list: loads on mount and whenever the filters change. */
function useBlogPostList(initialFilters: BlogPostFilters): BlogPostList {
  const [posts, setPosts] = useState<BlogPost[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<BlogPostFilters>(initialFilters);

  const fetchPosts = useCallback(
    async (activeFilters: BlogPostFilters = filters) => {
      try {
        setLoading(true);
        setError(null);
        const page = await fetchBlogPostPage(activeFilters);
        setPosts(page.items);
        setTotal(page.total);
      } catch (err) {
        setError(err instanceof Error ? err.message : "An error occurred");
      } finally {
        setLoading(false);
      }
    },
    [filters],
  );

  useEffect(() => {
    void fetchPosts(filters);
  }, [fetchPosts, filters]);

  return {
    posts,
    setPosts,
    total,
    loading,
    error,
    filters,
    setFilters,
    fetchPosts,
  };
}

function replacePost(
  setPosts: Dispatch<SetStateAction<BlogPost[]>>,
  post: BlogPost,
): void {
  setPosts((prev) => prev.map((p) => (p.id === post.id ? post : p)));
}

/**
 * Delete, refreshing the list (then throwing) when the lock was stale.
 *
 * A stale lock version refreshes the listing so a retry uses fresh data.
 */
async function deleteAndSync(
  { setPosts, fetchPosts }: BlogPostList,
  id: string,
  lockVersion: number,
): Promise<boolean> {
  const outcome = await deleteBlogPost(id, lockVersion);
  if (outcome === "carouselBlocked") {
    throw new BlogPostMutationError(BLOG_POST_ERR_CAROUSEL_DELETE_BLOCKED);
  }
  if (outcome === "versionConflict") {
    await fetchPosts();
    throw new BlogPostMutationError(BLOG_POST_ERR_VERSION_CONFLICT);
  }
  setPosts((prev) => prev.filter((p) => p.id !== id));
  return true;
}

/** Unpublish, refreshing the list (then throwing) when the lock was stale. */
async function unpublishAndSync(
  { setPosts, fetchPosts }: BlogPostList,
  id: string,
  lockVersion: number,
): Promise<BlogPost> {
  const post = await unpublishBlogPost(id, lockVersion);
  if (post === null) {
    await fetchPosts();
    throw new BlogPostMutationError(BLOG_POST_ERR_VERSION_CONFLICT);
  }
  replacePost(setPosts, post);
  return post;
}

/** Create/update/delete/unpublish plus the review workflow transitions. */
function blogPostMutations(list: BlogPostList) {
  const { setPosts, fetchPosts } = list;
  const transition =
    (action: string, failure: string) =>
    async (id: string): Promise<boolean> => {
      await postBlogPostAction(id, { action, failure });
      await fetchPosts();
      return true;
    };
  return {
    create: async (data: BlogPostCreatePayload) => {
      const post = await createBlogPost(data);
      setPosts((prev) => [post, ...prev]);
      return post;
    },
    update: async (
      id: string,
      data: BlogPostUpdatePayload,
      lockVersion: number,
    ) => {
      const post = await updateBlogPost(id, { data, lockVersion });
      replacePost(setPosts, post);
      return post;
    },
    delete: (id: string, lockVersion: number) =>
      deleteAndSync(list, id, lockVersion),
    unpublish: (id: string, lockVersion: number) =>
      unpublishAndSync(list, id, lockVersion),
    submitForReview: async (id: string, reviewerId: string) => {
      const action = `submit-review?reviewer_id=${encodeURIComponent(reviewerId)}`;
      return transition(action, "Failed to submit for review")(id);
    },
    approve: transition("approve", "Failed to approve blog post"),
    publish: transition("publish", "Failed to publish blog post"),
  };
}

export function useBlogPosts(initialFilters: BlogPostFilters = {}) {
  const list = useBlogPostList(initialFilters);
  const { posts, total, loading, error, filters, setFilters, fetchPosts } =
    list;
  return {
    posts,
    total,
    loading,
    error,
    filters,
    setFilters,
    refetch: fetchPosts,
    ...blogPostMutations(list),
  };
}
