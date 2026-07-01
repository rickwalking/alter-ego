import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { cookies } from "next/headers";
import { NeonBlogPostCard } from "@/modules/publishing";
import { BG_DEEP, TEXT, TEXT_MUTED } from "@/constants/neon";
import { PUBLIC_ROUTE_PATHS } from "@/constants/public-routes";
import {
  fetchCompletedProjects,
  fetchPublicBlogPosts,
} from "@/lib/server-fetch";
import { DEFAULT_LOCALE, SUPPORTED_LOCALES } from "@/i18n/config";
import type { SupportedLocale } from "@/i18n/config";
import type { CarouselProjectListResponse } from "@/schemas/carousel";
import type { NeonBlogPostCardProps } from "@/schemas/neon-blog-post-card";
import type { PublicBlogPostSummary } from "@/schemas/public-blog-post";

export const dynamic = "force-dynamic";

const BLOG_LIST_MAX_WIDTH_PX = 1200;
const BLOG_LIST_LIMIT = 20;
const SUBTITLE_MAX_WORDS = 15;

type CarouselProjectItem = CarouselProjectListResponse["items"][number];

function truncateWords(text: string, maxWords: number): string {
  const cleaned = text.replace(/\*\*|\*|__|\`|\[|\]|\(|\)/g, "").trim();
  const words = cleaned.split(/\s+/).filter((w) => w.length > 0);
  if (words.length <= maxWords) return cleaned;
  return words.slice(0, maxWords).join(" ") + "...";
}

function projectToCard(
  post: CarouselProjectItem,
  locale: SupportedLocale,
): NeonBlogPostCardProps {
  const rawSubtitle =
    locale === "en" ? post.subtitle_en || post.subtitle : post.subtitle;
  const tokens = post.design_tokens as
    | { images?: { hero?: string } }
    | null
    | undefined;
  return {
    id: post.id,
    title:
      (locale === "en" ? post.title_en || post.title : post.title) ||
      post.topic,
    subtitle: truncateWords(rawSubtitle || post.topic, SUBTITLE_MAX_WORDS),
    niche: post.niche ?? undefined,
    imageUrl: tokens?.images?.hero ?? "",
    createdAt: post.created_at,
    href: `/blog/${post.id}`,
  };
}

function publicPostToCard(post: PublicBlogPostSummary): NeonBlogPostCardProps {
  const subtitleSource = post.excerpt ?? post.meta_description ?? "";
  return {
    id: post.id,
    title: post.title,
    subtitle: subtitleSource
      ? truncateWords(subtitleSource, SUBTITLE_MAX_WORDS)
      : undefined,
    imageUrl: post.featured_image_url ?? undefined,
    createdAt: post.published_at ?? "",
    href: `/blog/${post.id}`,
  };
}

/**
 * AE-0297: the listing prefers the public blog-posts feed (published-only,
 * includes standalone posts); carousel-origin entries are enriched with their
 * project's localized copy + hero. On public-feed failure it falls open to
 * the carousel feed — today's already-public source, nothing new exposed.
 */
function buildCards(
  publicFeed: { items: PublicBlogPostSummary[] } | null,
  carouselFeed: CarouselProjectListResponse,
  locale: SupportedLocale,
): NeonBlogPostCardProps[] {
  if (!publicFeed) {
    return carouselFeed.items.map((post) => projectToCard(post, locale));
  }
  const byProject = new Map(
    carouselFeed.items.map((project) => [project.id, project]),
  );
  return publicFeed.items.map((post) => {
    const project = post.project_id
      ? byProject.get(post.project_id)
      : undefined;
    if (project) {
      return {
        ...projectToCard(project, locale),
        id: post.id,
        href: `/blog/${post.id}`,
      };
    }
    return publicPostToCard(post);
  });
}

export default async function PublicBlogListPage() {
  const t = await getTranslations("blog");
  const cookieStore = await cookies();
  const localeCookie = cookieStore.get("locale")?.value;
  const locale: SupportedLocale =
    localeCookie && SUPPORTED_LOCALES.includes(localeCookie as SupportedLocale)
      ? (localeCookie as SupportedLocale)
      : DEFAULT_LOCALE;

  const [publicFeed, carouselFeed] = await Promise.all([
    fetchPublicBlogPosts(BLOG_LIST_LIMIT),
    fetchCompletedProjects(BLOG_LIST_LIMIT),
  ]);
  const cards = buildCards(publicFeed, carouselFeed, locale);

  return (
    <div
      className="mx-auto px-6 py-12"
      style={{ maxWidth: `${BLOG_LIST_MAX_WIDTH_PX}px`, background: BG_DEEP }}
    >
      <Link
        href={PUBLIC_ROUTE_PATHS.HOME}
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "8px",
          marginBottom: "32px",
          fontSize: "14px",
          color: TEXT_MUTED,
          textDecoration: "none",
        }}
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="m12 19-7-7 7-7" />
          <path d="M19 12H5" />
        </svg>
        {t("backHome")}
      </Link>
      <h1
        style={{
          marginBottom: "8px",
          fontSize: "clamp(28px, 4vw, 40px)",
          fontWeight: 800,
          letterSpacing: "-0.02em",
          color: TEXT,
        }}
      >
        {t("title")}
      </h1>
      <p
        style={{
          marginBottom: "40px",
          fontSize: "18px",
          color: TEXT_MUTED,
          maxWidth: "640px",
        }}
      >
        {t("subtitle")}
      </p>
      {cards.length === 0 ? (
        <div
          style={{
            borderRadius: "12px",
            border: "1px dashed rgba(255,255,255,0.1)",
            padding: "48px",
            textAlign: "center",
          }}
        >
          <p style={{ fontSize: "16px", color: TEXT_MUTED }}>{t("noPosts")}</p>
        </div>
      ) : (
        <div
          style={{
            display: "grid",
            gap: "24px",
            gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
          }}
        >
          {cards.map((card) => (
            <NeonBlogPostCard key={card.id} {...card} />
          ))}
        </div>
      )}
    </div>
  );
}
