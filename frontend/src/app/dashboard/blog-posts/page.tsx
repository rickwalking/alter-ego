"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonSearchBar } from "@/components/molecules/neon-search-bar";
import { NeonTopBar } from "@/components/organisms/neon-top-bar";
import {
  BLOG_POSTS_I18N_NAMESPACE,
  filterBlogPosts,
  mapBlogPostToDashboard,
} from "@/modules/editorial-operations";
import { useBlogPosts } from "@/modules/publishing";
import { NeonSpinner } from "@/components/atoms/neon-spinner";
import { NEON_RED } from "@/constants/neon";
import { BlogPostsFilters } from "@/app/dashboard/blog-posts/blog-posts-filters";
import { BlogPostsList } from "@/app/dashboard/blog-posts/blog-posts-grid";
import { DeleteConfirmModal } from "@/app/dashboard/blog-posts/blog-posts-actions";
import { useNewBlogPost } from "@/app/dashboard/blog-posts/use-new-blog-post";
import { useBlogPostActions } from "@/app/dashboard/blog-posts/use-blog-post-actions";

/** API max page size — load as many posts as one request allows (AE-0411). */
const BLOG_POSTS_LIST_LIMIT = 100;

export default function BlogPostsPage(): React.ReactElement {
  const t = useTranslations(BLOG_POSTS_I18N_NAMESPACE);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const {
    posts,
    total,
    loading,
    error,
    create,
    delete: deletePost,
    unpublish,
  } = useBlogPosts({ limit: BLOG_POSTS_LIST_LIMIT });
  const { creating, createError, handleNewPost } = useNewBlogPost(create);
  const { actions, deleteTarget, actionError, confirmDelete, cancelDelete } =
    useBlogPostActions({ deletePost, unpublish });

  const dashboardPosts = posts.map(mapBlogPostToDashboard);

  const filteredPosts = filterBlogPosts(dashboardPosts, {
    search,
    statusFilter,
  });
  const notice = actionError ?? createError;

  return (
    <div
      className="flex-1 text-white relative"
      style={{ fontFamily: "Inter, system-ui, sans-serif" }}
    >
      <NeonTopBar
        title={t("title")}
        breadcrumb={[{ label: t("breadcrumbAll") }]}
        actions={
          <>
            <NeonSearchBar
              placeholder={t("searchPlaceholder")}
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
              {t("newPost")}
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
          <p
            className="text-center py-8"
            style={{ color: NEON_RED }}
            role="alert"
          >
            {t("errors.loadFailed")}
          </p>
        )}
        {notice && !loading && (
          <p
            className="text-center py-2"
            style={{ color: NEON_RED }}
            role="alert"
          >
            {notice}
          </p>
        )}
        {!loading && !error && (
          <>
            <BlogPostsFilters
              statusFilter={statusFilter}
              onStatusFilterChange={setStatusFilter}
              shownCount={filteredPosts.length}
              totalCount={Math.max(total, dashboardPosts.length)}
            />
            <BlogPostsList
              posts={filteredPosts}
              hasNoPosts={dashboardPosts.length === 0}
              actions={actions}
            />
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
