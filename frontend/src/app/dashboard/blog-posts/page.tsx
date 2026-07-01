"use client";

import { useState } from "react";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonSearchBar } from "@/components/molecules/neon-search-bar";
import { NeonTopBar } from "@/components/organisms/neon-top-bar";
import { filterBlogPosts } from "@/modules/editorial-operations";
import { mapBlogPostToDashboard } from "@/modules/editorial-operations";
import { useBlogPosts } from "@/modules/publishing";
import { NeonSpinner } from "@/components/atoms/neon-spinner";
import { NEON_RED } from "@/constants/neon";
import { BlogPostsFilters } from "@/app/dashboard/blog-posts/blog-posts-filters";
import {
  FeaturedBlogPost,
  RegularBlogPosts,
} from "@/app/dashboard/blog-posts/blog-posts-grid";
import { DeleteConfirmModal } from "@/app/dashboard/blog-posts/blog-posts-actions";
import { useNewBlogPost } from "@/app/dashboard/blog-posts/use-new-blog-post";
import { useBlogPostActions } from "@/app/dashboard/blog-posts/use-blog-post-actions";

export default function BlogPostsPage(): React.ReactElement {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const {
    posts,
    loading,
    error,
    create,
    delete: deletePost,
    unpublish,
  } = useBlogPosts();
  const { creating, handleNewPost } = useNewBlogPost(create);
  const { actions, deleteTarget, actionError, confirmDelete, cancelDelete } =
    useBlogPostActions({ deletePost, unpublish });

  const dashboardPosts = posts.map(mapBlogPostToDashboard);

  const filteredPosts = filterBlogPosts(dashboardPosts, {
    search,
    statusFilter,
    categoryFilter,
  });

  const featuredPost = filteredPosts.find((post) => post.featured);
  const regularPosts = filteredPosts.filter((post) => !post.featured);

  return (
    <div
      className="flex-1 text-white relative"
      style={{ fontFamily: "Inter, system-ui, sans-serif" }}
    >
      <NeonTopBar
        title="Blog Posts"
        breadcrumb={[{ label: "all posts" }]}
        actions={
          <>
            <NeonSearchBar
              placeholder="Search posts..."
              value={search}
              onChange={setSearch}
              className="w-full sm:w-[200px]"
            />
            <NeonButton
              size="sm"
              disabled={creating}
              onClick={() => void handleNewPost()}
              icon={
                <svg
                  width="14"
                  height="14"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <path d="M12 5v14" strokeLinecap="round" />
                  <path d="M5 12h14" strokeLinecap="round" />
                </svg>
              }
            >
              New Post
            </NeonButton>
          </>
        }
      />

      <div className="p-7 flex flex-col gap-4">
        {loading && (
          <div className="flex justify-center py-12">
            <NeonSpinner size="lg" />
          </div>
        )}
        {error && !loading && (
          <p className="text-center py-8" style={{ color: NEON_RED }}>
            {error}
          </p>
        )}
        {actionError && !loading && (
          <p
            className="text-center py-2"
            style={{ color: NEON_RED }}
            role="alert"
          >
            {actionError}
          </p>
        )}
        {!loading && !error && (
          <>
            <BlogPostsFilters
              statusFilter={statusFilter}
              categoryFilter={categoryFilter}
              onStatusFilterChange={setStatusFilter}
              onCategoryFilterChange={setCategoryFilter}
            />

            <div className="grid gap-4">
              {featuredPost && (
                <FeaturedBlogPost post={featuredPost} actions={actions} />
              )}
              <RegularBlogPosts posts={regularPosts} actions={actions} />
            </div>
          </>
        )}
      </div>
      <DeleteConfirmModal
        post={deleteTarget}
        onConfirm={() => void confirmDelete()}
        onCancel={cancelDelete}
      />
    </div>
  );
}
