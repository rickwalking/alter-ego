"use client";

import { useState } from "react";
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
      {/* Top Bar */}
      <div className="h-[56px] flex items-center justify-between px-6 border-b border-[rgba(0,212,255,0.06)] bg-[rgba(6,10,18,0.6)] backdrop-blur-xl sticky top-0 z-30">
        <div className="flex items-center gap-3">
          <h1 className="text-[16px] font-bold">Blog Posts</h1>
          <div className="font-mono text-[11px] text-[rgba(255,255,255,0.3)]">
            / <span>all posts</span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <input
            type="search"
            style={{
              padding: "6px 12px",
              borderRadius: "4px",
              background: "rgba(0,0,0,0.2)",
              border: "1px solid rgba(0,212,255,0.08)",
              color: "rgba(255,255,255,0.55)",
              fontSize: "13px",
              width: "200px",
              outline: "none",
              fontFamily: "'JetBrains Mono', ui-monospace, monospace",
            }}
            placeholder="Search posts..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <button
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "6px 14px",
              borderRadius: "4px",
              border: "none",
              background: "linear-gradient(135deg, #00d4ff 0%, #0090b0 100%)",
              color: "#060a12",
              fontFamily: "Inter, system-ui, sans-serif",
              fontSize: "12px",
              fontWeight: 700,
              cursor: "pointer",
              transition: "all 0.15s",
            }}
          >
            <svg
              width="14"
              height="14"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              viewBox="0 0 24 24"
            >
              <path d="M12 5v14" strokeLinecap="round" />
              <path d="M5 12h14" strokeLinecap="round" />
            </svg>
            New Post
          </button>
        </div>
      </div>

      <div className="p-7 flex flex-col gap-4">
        {/* Filters */}
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex gap-2">
            <select
              style={{
                padding: "6px 30px 6px 10px",
                fontSize: "12px",
                border: "1px solid rgba(0,212,255,0.15)",
                background: "rgba(6,10,18,0.45)",
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
                border: "1px solid rgba(0,212,255,0.15)",
                background: "rgba(6,10,18,0.45)",
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
              color: "rgba(255,255,255,0.3)",
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
                  background:
                    "linear-gradient(135deg, rgba(0,212,255,0.1), rgba(255,39,112,0.06))",
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
                className="bg-[#0d1324] border border-[rgba(255,255,255,0.06)] rounded p-[16px] overflow-hidden transition-all duration-250 cursor-pointer hover:border-[rgba(0,212,255,0.15)] hover:-translate-y-0.5 active:translate-y-[-2px]"
              >
                <div
                  className="w-full h-[160px] mb-4 transition-all duration-250"
                  style={{
                    background:
                      "linear-gradient(135deg, rgba(0,212,255,0.08), rgba(255,39,112,0.04))",
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
