import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { getRequestLocale } from "@/i18n/request-locale";
import { NeonBlogPostCard } from "@/modules/publishing";
import { BG_DEEP, TEXT, TEXT_MUTED } from "@/constants/neon";
import { PUBLIC_ROUTE_PATHS } from "@/constants/public-routes";
import { buildPublicBlogCards } from "@/lib/public-blog-cards";
import {
  fetchCompletedProjects,
  fetchPublicBlogPosts,
} from "@/lib/server-fetch";

export const dynamic = "force-dynamic";

const BLOG_LIST_MAX_WIDTH_PX = 1200;
const BLOG_LIST_LIMIT = 20;

export default async function PublicBlogListPage() {
  const t = await getTranslations("blog");
  const locale = await getRequestLocale();

  const [publicFeed, carouselFeed] = await Promise.all([
    fetchPublicBlogPosts(BLOG_LIST_LIMIT),
    fetchCompletedProjects(BLOG_LIST_LIMIT),
  ]);
  const cards = buildPublicBlogCards({ publicFeed, carouselFeed, locale });

  return (
    <div
      className="mx-auto px-4 py-12 sm:px-6"
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
            gridTemplateColumns:
              "repeat(auto-fill, minmax(min(280px, 100%), 1fr))",
          }}
        >
          {cards.map((card) => (
            <NeonBlogPostCard
              key={card.id}
              {...card}
              title={card.title || t("untitledPost")}
              locale={locale}
            />
          ))}
        </div>
      )}
    </div>
  );
}
