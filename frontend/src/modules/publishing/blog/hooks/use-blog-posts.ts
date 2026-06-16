"use client";

/**
 * Custom hook for managing blog posts with search/filter (UI-028).
 */

import { useCallback, useEffect, useState } from "react";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { HTTP_HEADER_IF_MATCH } from "@/constants/workflow";
import type {
  BlogPost,
  BlogPostCreatePayload,
  BlogPostUpdatePayload,
} from "../types";

const API_BASE = "/api";

export interface BlogPostFilters {
  status?: string;
  search?: string;
  limit?: number;
  offset?: number;
}

export function useBlogPosts(initialFilters: BlogPostFilters = {}) {
  const [posts, setPosts] = useState<BlogPost[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<BlogPostFilters>(initialFilters);

  const fetchPosts = useCallback(
    async (activeFilters: BlogPostFilters = filters) => {
      try {
        setLoading(true);
        const params = new URLSearchParams();
        if (activeFilters.status) params.set("status", activeFilters.status);
        if (activeFilters.search) params.set("search", activeFilters.search);
        if (activeFilters.limit)
          params.set("limit", String(activeFilters.limit));
        if (activeFilters.offset)
          params.set("offset", String(activeFilters.offset));
        const qs = params.toString();
        const response = await authenticatedFetch(
          `${API_BASE}/blog-posts${qs ? `?${qs}` : ""}`,
        );
        if (!response.ok) {
          throw new Error("Failed to fetch blog posts");
        }
        const data = await response.json();
        setPosts(data.items);
        setTotal(data.total ?? data.items.length);
      } catch (err) {
        setError(err instanceof Error ? err.message : "An error occurred");
      } finally {
        setLoading(false);
      }
    },
    [filters],
  );

  const createPost = async (data: BlogPostCreatePayload) => {
    const response = await authenticatedFetch(`${API_BASE}/blog-posts`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error("Failed to create blog post");
    const post = await response.json();
    setPosts((prev) => [post, ...prev]);
    return post;
  };

  const updatePost = async (
    id: string,
    data: BlogPostUpdatePayload,
    lockVersion: number,
  ) => {
    const response = await authenticatedFetch(`${API_BASE}/blog-posts/${id}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        [HTTP_HEADER_IF_MATCH]: String(lockVersion),
      },
      body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error("Failed to update blog post");
    const post = await response.json();
    setPosts((prev) => prev.map((p) => (p.id === id ? post : p)));
    return post;
  };

  const deletePost = async (id: string) => {
    const response = await authenticatedFetch(`${API_BASE}/blog-posts/${id}`, {
      method: "DELETE",
    });
    if (!response.ok) throw new Error("Failed to delete blog post");
    setPosts((prev) => prev.filter((p) => p.id !== id));
    return true;
  };

  const submitForReview = async (id: string, reviewerId: string) => {
    const response = await authenticatedFetch(
      `${API_BASE}/blog-posts/${id}/submit-review?reviewer_id=${encodeURIComponent(reviewerId)}`,
      { method: "POST" },
    );
    if (!response.ok) throw new Error("Failed to submit for review");
    await fetchPosts();
    return true;
  };

  const approvePost = async (id: string) => {
    const response = await authenticatedFetch(
      `${API_BASE}/blog-posts/${id}/approve`,
      {
        method: "POST",
      },
    );
    if (!response.ok) throw new Error("Failed to approve blog post");
    await fetchPosts();
    return true;
  };

  const publishPost = async (id: string) => {
    const response = await authenticatedFetch(
      `${API_BASE}/blog-posts/${id}/publish`,
      {
        method: "POST",
      },
    );
    if (!response.ok) throw new Error("Failed to publish blog post");
    await fetchPosts();
    return true;
  };

  useEffect(() => {
    void fetchPosts(filters);
  }, [fetchPosts, filters]);

  return {
    posts,
    total,
    loading,
    error,
    filters,
    setFilters,
    refetch: fetchPosts,
    create: createPost,
    update: updatePost,
    delete: deletePost,
    submitForReview,
    approve: approvePost,
    publish: publishPost,
  };
}
