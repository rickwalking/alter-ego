import Link from "next/link";
import Image from "next/image";
import {
  BG_SURFACE,
  NEON_MAGENTA,
  NEON_TEAL,
  TEXT_DIM,
  TEXT_MUTED,
} from "@/constants/neon";
import { toPublicCarouselImageUrl } from "@/lib/carousel-media-url";
import { truncateWords } from "@/app/(public)/(marketing)/marketing-helpers";
import type { MarketingPostProps } from "@/app/(public)/(marketing)/types";

function localizedTitle(post: MarketingPostProps["post"], locale: string): string {
  return locale === "en"
    ? post.title_en || post.title || post.topic
    : post.title || post.topic;
}

function localizedSubtitle(
  post: MarketingPostProps["post"],
  locale: string,
): string {
  return locale === "en"
    ? post.subtitle_en || post.subtitle || post.topic
    : post.subtitle || post.topic;
}

function heroImageUrl(post: MarketingPostProps["post"]): string {
  const tokens = post.design_tokens as
    | { images?: { hero?: string } }
    | null
    | undefined;
  const rawHero = tokens?.images?.hero ?? "";
  return rawHero ? toPublicCarouselImageUrl(rawHero) : "";
}

function formatPostDate(createdAt: string): string {
  return new Date(createdAt).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function FeaturedPostImage({
  imageUrl,
}: {
  imageUrl: string;
}): React.ReactElement {
  return (
    <div
      style={{
        height: "220px",
        background: `linear-gradient(135deg, rgba(0,212,255,0.08), rgba(255,39,112,0.04))`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "'JetBrains Mono', ui-monospace, monospace",
        fontSize: "13px",
        color: TEXT_DIM,
        position: "relative",
        overflow: "hidden",
      }}
    >
      {imageUrl ? (
        <Image
          src={imageUrl}
          alt=""
          fill
          className="object-cover"
          sizes="(max-width: 768px) 100vw, 50vw"
          unoptimized={
            imageUrl.startsWith("http") || imageUrl.startsWith("/api/")
          }
        />
      ) : (
        <span>▸ carousel_preview.jpg</span>
      )}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: `linear-gradient(to top, ${BG_SURFACE} 0%, transparent 50%)`,
        }}
      />
    </div>
  );
}

export function FeaturedPostCard({
  post,
  locale,
}: MarketingPostProps): React.ReactElement {
  return (
    <Link
      href={`/blog/${post.id}`}
      className="transform rounded-xl overflow-hidden border border-[rgba(0,212,255,0.1)] bg-bg-surface flex flex-col no-underline text-inherit transition-all duration-300 min-w-0 hover:border-[rgba(0,212,255,0.2)] hover:shadow-[0_0_30px_rgba(0,212,255,0.03)] hover:-translate-y-1 active:-translate-y-1 motion-reduce:hover:translate-y-0 motion-reduce:active:translate-y-0"
    >
      <FeaturedPostImage imageUrl={heroImageUrl(post)} />
      <div
        style={{
          padding: "28px",
          flex: 1,
          display: "flex",
          flexDirection: "column",
        }}
      >
        <span
          style={{
            display: "inline-flex",
            alignSelf: "flex-start",
            padding: "3px 10px",
            fontFamily: "'JetBrains Mono', ui-monospace, monospace",
            fontSize: "10px",
            fontWeight: 700,
            textTransform: "uppercase",
            letterSpacing: "2px",
            borderRadius: "3px",
            color: NEON_MAGENTA,
            background: "rgba(255,39,112,0.15)",
            border: `1px solid rgba(255,39,112,0.15)`,
            marginBottom: "12px",
          }}
        >
          {post.niche || "Post"}
        </span>
        <h3
          style={{
            fontSize: "20px",
            fontWeight: 800,
            letterSpacing: "-0.02em",
            marginBottom: "8px",
          }}
        >
          {localizedTitle(post, locale)}
        </h3>
        <p
          style={{
            fontSize: "14px",
            color: TEXT_MUTED,
            lineHeight: 1.7,
            flex: 1,
          }}
        >
          {truncateWords(localizedSubtitle(post, locale), 15)}
        </p>
        <span
          style={{
            fontFamily: "'JetBrains Mono', ui-monospace, monospace",
            fontSize: "11px",
            color: TEXT_DIM,
            marginTop: "16px",
          }}
        >
          {formatPostDate(post.created_at)}
        </span>
      </div>
    </Link>
  );
}

export function SecondaryPostLink({
  post,
  locale,
}: MarketingPostProps): React.ReactElement {
  return (
    <Link
      href={`/blog/${post.id}`}
      className="rounded-lg border border-neon-card-border bg-bg-card p-5 no-underline text-inherit block transition-all duration-300 min-w-0 hover:border-white/10 hover:bg-bg-elevated"
    >
      <span
        style={{
          fontFamily: "'JetBrains Mono', ui-monospace, monospace",
          fontSize: "9px",
          textTransform: "uppercase",
          letterSpacing: "2px",
          color: NEON_TEAL,
          marginBottom: "6px",
          display: "block",
        }}
      >
        {post.niche || "Post"}
      </span>
      <h4
        style={{
          fontSize: "14px",
          fontWeight: 600,
          marginBottom: "4px",
          lineHeight: 1.4,
        }}
      >
        {localizedTitle(post, locale)}
      </h4>
      <span
        style={{
          fontFamily: "'JetBrains Mono', ui-monospace, monospace",
          fontSize: "10px",
          color: TEXT_DIM,
        }}
      >
        {formatPostDate(post.created_at)}
      </span>
    </Link>
  );
}
