"use client";

import { useTranslations } from "next-intl";
import {
  BlogPostBadge,
  BlogPostStatusBadge,
} from "@/modules/editorial-operations";
import { formatBlogPostDate } from "@/modules/editorial-operations";
import { BLOG_POSTS_I18N_NAMESPACE } from "@/modules/editorial-operations";
import {
  BG_CARD,
  NEON_CARD_BORDER,
  NEON_CARD_HOVER_BORDER,
  NEON_GRADIENT_CARD,
  NEON_GRADIENT_FEATURED,
} from "@/constants/neon";
import type {
  BlogPostCardProps,
  BlogPostMetaProps,
  FeaturedBlogPostProps,
  RegularBlogPostsProps,
} from "@/app/dashboard/blog-posts/types";

function BlogPostMeta({ post }: BlogPostMetaProps): React.ReactElement {
  return (
    <div className="flex items-center justify-between mt-3 pt-3 border-t border-[rgba(255,255,255,0.04)]">
      <span className="font-mono text-[10px] text-[rgba(255,255,255,0.3)]">
        {formatBlogPostDate(post.date)}
      </span>
      <div className="flex gap-1.5 font-mono text-[10px] text-[rgba(255,255,255,0.3)]">
        <span>👁 {post.views.toLocaleString()}</span>
        <span>💬 {post.comments}</span>
      </div>
    </div>
  );
}

export function FeaturedBlogPost({
  post,
}: FeaturedBlogPostProps): React.ReactElement {
  const t = useTranslations(BLOG_POSTS_I18N_NAMESPACE);
  return (
    <div className="grid grid-cols-1 gap-0 md:grid-cols-2">
      <div
        className="relative overflow-hidden transition-all duration-250"
        style={{
          height: "240px",
          background: NEON_GRADIENT_FEATURED,
        }}
      />
      <div className="p-6 flex flex-col justify-center">
        <div className="flex gap-1.5 mb-2.5">
          <BlogPostStatusBadge status={post.status} />
          <BlogPostBadge color="cyan">{t("featured")}</BlogPostBadge>
        </div>
        <h3 className="text-[20px] font-bold leading-tight mb-2">
          {post.title}
        </h3>
        <p className="text-[13px] leading-relaxed text-[rgba(255,255,255,0.88)] line-clamp-3">
          {post.excerpt}
        </p>
        <BlogPostMeta post={post} />
      </div>
    </div>
  );
}

export function BlogPostCard({ post }: BlogPostCardProps): React.ReactElement {
  return (
    <div
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
        <BlogPostStatusBadge status={post.status} />
        <h3 className="text-[15px] font-bold leading-snug mb-1.5">
          {post.title}
        </h3>
        <p className="text-[12px] leading-relaxed text-[rgba(255,255,255,0.55)] line-clamp-2">
          {post.excerpt}
        </p>
        <BlogPostMeta post={post} />
      </div>
    </div>
  );
}

export function RegularBlogPosts({
  posts,
}: RegularBlogPostsProps): React.ReactElement {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      {posts.map((post) => (
        <BlogPostCard key={post.id} post={post} />
      ))}
    </div>
  );
}
