"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";

const STATUS_OPTIONS = [
  { value: "", label: "All Status" },
  { value: "published", label: "Published" },
  { value: "draft", label: "Draft" },
  { value: "review", label: "Review" },
];

const CATEGORY_OPTIONS = [
  { value: "", label: "All Categories" },
  { value: "AI", label: "AI" },
  { value: "Security", label: "Security" },
  { value: "Architecture", label: "Architecture" },
  { value: "Dev", label: "Dev" },
];

const BADGE_COLORS: Record<string, { bg: string; text: string }> = {
  security: { bg: "rgba(255,39,112,0.12)", text: "#ff2770" },
  ai: { bg: "rgba(10,197,168,0.12)", text: "#0ac5a8" },
  architecture: { bg: "rgba(168,85,247,0.12)", text: "#a855f7" },
  dev: { bg: "rgba(245,158,11,0.12)", text: "#f59e0b" },
  magenta: { bg: "rgba(255,39,112,0.12)", text: "#ff2770" },
  teal: { bg: "rgba(10,197,168,0.12)", text: "#0ac5a8" },
  cyan: { bg: "rgba(0,212,255,0.12)", text: "#00d4ff" },
  purple: { bg: "rgba(168,85,247,0.12)", text: "#a855f7" },
  amber: { bg: "rgba(245,158,11,0.12)", text: "#f59e0b" },
  red: { bg: "rgba(239,68,68,0.12)", text: "#ef4444" },
  featured: { bg: "rgba(0,212,255,0.12)", text: "#00d4ff" },
};

const BADGE_CLASS = "badge";

function Badge({
  children,
  color,
}: {
  children: React.ReactNode;
  color: string;
}) {
  const { bg, text } = BADGE_COLORS[color];
  return (
    <span
      className={`${BADGE_CLASS} ${BADGE_CLASS}-${color}`}
      style={{ backgroundColor: bg, color: text }}
    >
      {children}
    </span>
  );
}

const MOCK_POSTS = [
  {
    id: "1",
    title: "3800 repositorios internos do GitHub expostos",
    excerpt:
      "Deep analysis of the massive GitHub internal repository leak and what it means for software development security practices in 2026.",
    date: "May 26, 2026",
    views: 2400,
    comments: 48,
    category: "Security",
    featured: true,
  },
  {
    id: "2",
    title: "Claude Sonnet 4 vs GPT-5: Comparing the latest LLMs",
    excerpt:
      "Benchmark comparison of coding, reasoning, and agentic capabilities between the two leading models.",
    date: "May 24, 2026",
    views: 1800,
    comments: 32,
    category: "AI",
    featured: false,
  },
  {
    id: "3",
    title: "Building RAG Pipelines with LangGraph and Deep Agents",
    excerpt:
      "How to orchestrate complex multi-agent workflows using LangGraph's state machine and subagent patterns.",
    date: "May 20, 2026",
    views: 3100,
    comments: 56,
    category: "Architecture",
    featured: false,
  },
  {
    id: "4",
    title: "Event-Driven Workflows: Why We Chose Redis Streams",
    excerpt:
      "A technical deep dive into our event-driven architecture and the tradeoffs that led us to Redis Streams.",
    date: "May 15, 2026",
    views: 1200,
    comments: 18,
    category: "Dev",
    featured: false,
  },
  {
    id: "5",
    title: "Zero-Day Supply Chain Attacks in Open Source",
    excerpt:
      "Understanding the attack surface of modern open source dependencies and mitigation strategies.",
    date: "May 10, 2026",
    views: 890,
    comments: 12,
    category: "Security",
    featured: false,
  },
  {
    id: "6",
    title: "DeepSeek V4: The Open-Source AI Race Just Changed",
    excerpt:
      "Full analysis of DeepSeek V4's architecture, pricing, and competitive positioning against closed models.",
    date: "May 8, 2026",
    views: 4200,
    comments: 89,
    category: "AI",
    featured: false,
  },
];

function formatDate(date: string): string {
  return new Date(date).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export default function BlogPostsPage() {
  const t = useTranslations("dashboard.blogPosts");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");

  const filteredPosts = MOCK_POSTS.filter((post) => {
    if (
      statusFilter &&
      post.category.toLowerCase() !== statusFilter.toLowerCase()
    )
      return false;
    if (
      categoryFilter &&
      post.category.toLowerCase() !== categoryFilter.toLowerCase()
    )
      return false;
    if (
      search &&
      !post.title.toLowerCase().includes(search.toLowerCase()) &&
      !post.excerpt.toLowerCase().includes(search.toLowerCase())
    )
      return false;
    return true;
  });

  const featuredPost = filteredPosts.find((p) => p.featured);
  const regularPosts = filteredPosts.filter((p) => !p.featured);

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
              {STATUS_OPTIONS.map((opt) => (
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
              {CATEGORY_OPTIONS.map((opt) => (
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
                  <Badge color="magenta">Security</Badge>
                  <Badge color="cyan">Featured</Badge>
                </div>
                <h3 className="text-[20px] font-bold leading-tight mb-2">
                  {featuredPost.title}
                </h3>
                <p className="text-[13px] leading-relaxed text-[rgba(255,255,255,0.88)] line-clamp-3">
                  {featuredPost.excerpt}
                </p>
                <div className="flex items-center justify-between mt-3 pt-3 border-t border-[rgba(255,255,255,0.04)]">
                  <span className="font-mono text-[10px] text-[rgba(255,255,255,0.3)]">
                    {formatDate(featuredPost.date)}
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
                    <Badge color={post.category.toLowerCase()}>
                      {post.category}
                    </Badge>
                  )}
                  <h3 className="text-[15px] font-bold leading-snug mb-1.5">
                    {post.title}
                  </h3>
                  <p className="text-[12px] leading-relaxed text-[rgba(255,255,255,0.55)] line-clamp-2">
                    {post.excerpt}
                  </p>
                  <div className="flex items-center justify-between mt-3 pt-3 border-t border-[rgba(255,255,255,0.04)]">
                    <span className="font-mono text-[10px] text-[rgba(255,255,255,0.3)]">
                      {formatDate(post.date)}
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
