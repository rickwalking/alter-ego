"use client";

import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonSearchBar } from "@/components/molecules/neon-search-bar";
import { NeonTopBar } from "@/components/organisms/neon-top-bar";
import {
  BLOG_POSTS_I18N_NAMESPACE,
  mapBlogPostToDashboard,
} from "@/modules/editorial-operations";
import { useBlogPosts } from "@/modules/publishing";
import { NeonSpinner } from "@/components/atoms/neon-spinner";
import { NEON_RED } from "@/constants/neon";
import { BlogPostsFilters } from "@/app/dashboard/blog-posts/blog-posts-filters";
import { BlogPostsList } from "@/app/dashboard/blog-posts/blog-posts-grid";
import { DeleteConfirmModal } from "@/app/dashboard/blog-posts/blog-posts-actions";
import { useNewBlogPost } from "@/app/dashboard/blog-posts/use-new-blog-post";
import { GenerateBlogPostAction } from "@/app/dashboard/blog-posts/generate-blog-post-modal";
import { useBlogPostActions } from "@/app/dashboard/blog-posts/use-blog-post-actions";
import { BlogPostsPager } from "@/app/dashboard/blog-posts/blog-posts-pager";
import {
  blogPostsPageCount,
  blogPostsPageFilters,
} from "@/app/dashboard/blog-posts/blog-posts-paging";
import {
  INITIAL_BLOG_POST_LIST_QUERY,
  useBlogPostsPaging,
} from "@/app/dashboard/blog-posts/use-blog-posts-paging";

interface BlogPostsStatusProps {
  loading: boolean;
  loadError: string | null;
  notice: string | null;
}

/** The spinner while loading; otherwise the load error and the action notice. */
function BlogPostsStatus({
  loading,
  loadError,
  notice,
}: Readonly<BlogPostsStatusProps>): React.ReactElement | null {
  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <NeonSpinner size="lg" />
      </div>
    );
  }
  return (
    <>
      {loadError ? (
        <p
          className="text-center py-8"
          style={{ color: NEON_RED }}
          role="alert"
        >
          {loadError}
        </p>
      ) : null}
      {notice ? (
        <p
          className="text-center py-2"
          style={{ color: NEON_RED }}
          role="alert"
        >
          {notice}
        </p>
      ) : null}
    </>
  );
}

/**
 * Lists one API page at a time; status and search filter on the server. The
 * status filter stays mounted while a new page loads.
 */
export default function BlogPostsPage(): React.ReactElement {
  const t = useTranslations(BLOG_POSTS_I18N_NAMESPACE);
  const {
    posts,
    total,
    loading,
    error,
    setFilters,
    create,
    delete: deletePost,
    unpublish,
  } = useBlogPosts(blogPostsPageFilters(INITIAL_BLOG_POST_LIST_QUERY));
  const paging = useBlogPostsPaging(setFilters);
  const { creating, createError, handleNewPost } = useNewBlogPost(create);
  const { actions, deleteTarget, actionError, confirmDelete, cancelDelete } =
    useBlogPostActions({ deletePost, unpublish });

  const dashboardPosts = posts.map(mapBlogPostToDashboard);
  const isFiltered = paging.statusFilter !== "" || paging.searchInput !== "";
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
              value={paging.searchInput}
              onChange={paging.changeSearch}
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
            <GenerateBlogPostAction />
          </>
        }
      />

      <div className="p-7 flex flex-col gap-4">
        {!error && (
          <BlogPostsFilters
            statusFilter={paging.statusFilter}
            onStatusFilterChange={paging.changeStatus}
            shownCount={dashboardPosts.length}
            totalCount={Math.max(total, dashboardPosts.length)}
          />
        )}
        <BlogPostsStatus
          loading={loading}
          loadError={error ? t("errors.loadFailed") : null}
          notice={notice}
        />
        {!loading && !error && (
          <>
            <BlogPostsList
              posts={dashboardPosts}
              hasNoPosts={!isFiltered && total === 0}
              actions={actions}
            />
            <BlogPostsPager
              page={paging.page}
              pageCount={blogPostsPageCount(total)}
              onPageChange={paging.goToPage}
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
