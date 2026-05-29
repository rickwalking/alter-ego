"use client";

import { useState } from "react";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonSearchBar } from "@/components/molecules/neon-search-bar";
import { NeonTopBar } from "@/components/organisms/neon-top-bar";
import { BlogPostBadge } from "@/features/dashboard/blog-posts/components/badge";
import {
  BLOG_POST_CATEGORY_OPTIONS,
  BLOG_POST_STATUS_OPTIONS,
} from "@/features/dashboard/blog-posts/constants";
import {
  filterBlogPosts,
  formatBlogPostDate,
} from "@/features/dashboard/blog-posts/helpers";
import { MOCK_BLOG_POSTS } from "@/features/dashboard/blog-posts/mock-data";
import {
  BG_CARD,
  NEON_BORDER_STRONG,
  NEON_CARD_BORDER,
  NEON_CARD_HOVER_BORDER,
  NEON_GRADIENT_CARD,
  NEON_GRADIENT_FEATURED,
  NEON_INPUT_BG,
  TEXT_DIM,
} from "@/constants/neon";

export default function BlogPostsPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");

  const filteredPosts = filterBlogPosts(MOCK_BLOG_POSTS, {
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
              className="w-[200px]"
            />
            <NeonButton
              size="sm"
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
        {/* Filters */}
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex gap-2">
            <select
              style={{
                padding: "6px 30px 6px 10px",
                fontSize: "12px",
                border: `1px solid ${NEON_BORDER_STRONG}`,
                background: NEON_INPUT_BG,
                color: "white",
                borderRadius: "4px",
                fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                outline: "none",
              }}
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              {BLOG_POST_STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            <select
              style={{
                padding: "6px 30px 6px 10px",
                fontSize: "12px",
                border: `1px solid ${NEON_BORDER_STRONG}`,
                background: NEON_INPUT_BG,
                color: "white",
                borderRadius: "4px",
                fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                outline: "none",
              }}
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
            >
              {BLOG_POST_CATEGORY_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
          <span
            style={{
              fontFamily: "'JetBrains Mono', ui-monospace, monospace",
              fontSize: "11px",
              color: TEXT_DIM,
            }}
          >
            24 posts
          </span>
        </div>

        <div className="grid gap-4">
          {featuredPost && (
            <div
              className="grid grid-cols-2 gap-0"
              style={{ gridTemplateColumns: "1fr 1fr" }}
            >
              <div
                className="relative overflow-hidden transition-all duration-250"
                style={{
                  height: "240px",
                  background: NEON_GRADIENT_FEATURED,
                }}
              />
              <div className="p-6 flex flex-col justify-center">
                <div className="flex gap-1.5 mb-2.5">
                  <BlogPostBadge color="magenta">Security</BlogPostBadge>
                  <BlogPostBadge color="cyan">Featured</BlogPostBadge>
                </div>
                <h3 className="text-[20px] font-bold leading-tight mb-2">
                  {featuredPost.title}
                </h3>
                <p className="text-[13px] leading-relaxed text-[rgba(255,255,255,0.88)] line-clamp-3">
                  {featuredPost.excerpt}
                </p>
                <div className="flex items-center justify-between mt-3 pt-3 border-t border-[rgba(255,255,255,0.04)]">
                  <span className="font-mono text-[10px] text-[rgba(255,255,255,0.3)]">
                    {formatBlogPostDate(featuredPost.date)}
                  </span>
                  <div className="flex gap-1.5 font-mono text-[10px] text-[rgba(255,255,255,0.3)]">
                    <span>👁 {featuredPost.views.toLocaleString()}</span>
                    <span>💬 {featuredPost.comments}</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div
            className="grid grid-cols-2 gap-4"
            style={{ gridTemplateColumns: "1fr 1fr" }}
          >
            {regularPosts.map((post) => (
              <div
                key={post.id}
                className="rounded p-[16px] overflow-hidden transition-all duration-250 cursor-pointer hover:-translate-y-0.5 active:translate-y-[-2px]"
                style={{
                  background: BG_CARD,
                  border: `1px solid ${NEON_CARD_BORDER}`,
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = NEON_CARD_HOVER_BORDER;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = NEON_CARD_BORDER;
                }}
              >
                <div
                  className="w-full h-[160px] mb-4 transition-all duration-250"
                  style={{
                    background: NEON_GRADIENT_CARD,
                  }}
                />
                <div>
                  {post.category && (
                    <BlogPostBadge color={post.category.toLowerCase()}>
                      {post.category}
                    </BlogPostBadge>
                  )}
                  <h3 className="text-[15px] font-bold leading-snug mb-1.5">
                    {post.title}
                  </h3>
                  <p className="text-[12px] leading-relaxed text-[rgba(255,255,255,0.55)] line-clamp-2">
                    {post.excerpt}
                  </p>
                  <div className="flex items-center justify-between mt-3 pt-3 border-t border-[rgba(255,255,255,0.04)]">
                    <span className="font-mono text-[10px] text-[rgba(255,255,255,0.3)]">
                      {formatBlogPostDate(post.date)}
                    </span>
                    <div className="flex gap-1.5 font-mono text-[10px] text-[rgba(255,255,255,0.3)]">
                      <span>👁 {post.views.toLocaleString()}</span>
                      <span>💬 {post.comments}</span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
