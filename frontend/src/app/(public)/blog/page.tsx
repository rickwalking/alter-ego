import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { cookies } from "next/headers";
import { NeonBlogPostCard } from "@/components/organisms/neon-blog-post-card";
import { BG_DEEP, TEXT, TEXT_MUTED } from "@/constants/neon";
import { PUBLIC_ROUTE_PATHS } from "@/constants/public-routes";
import { fetchCompletedProjects } from "@/lib/server-fetch";
import { DEFAULT_LOCALE, SUPPORTED_LOCALES } from "@/i18n/config";
import type { SupportedLocale } from "@/i18n/config";
import type { CarouselProjectListResponse } from "@/schemas/carousel";

export const dynamic = "force-dynamic";

const BLOG_LIST_MAX_WIDTH_PX = 1200;

function truncateWords(text: string, maxWords: number): string {
  const cleaned = text.replace(/\*\*|\*|__|\`|\[|\]|\(|\)/g, "").trim();
  const words = cleaned.split(/\s+/).filter((w) => w.length > 0);
  if (words.length <= maxWords) return cleaned;
  return words.slice(0, maxWords).join(" ") + "...";
}

export default async function PublicBlogListPage() {
  const t = await getTranslations("blog");
  const cookieStore = await cookies();
  const localeCookie = cookieStore.get("locale")?.value;
  const locale: SupportedLocale =
    localeCookie && SUPPORTED_LOCALES.includes(localeCookie as SupportedLocale)
      ? (localeCookie as SupportedLocale)
      : DEFAULT_LOCALE;

  const data: CarouselProjectListResponse = await fetchCompletedProjects(20);

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
      {data.items.length === 0 ? (
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
          {data.items.map((post) => {
            const rawSubtitle =
              locale === "en"
                ? post.subtitle_en || post.subtitle
                : post.subtitle;
            const subtitle = truncateWords(rawSubtitle || post.topic, 15);
            const tokens = post.design_tokens as
              | { images?: { hero?: string } }
              | null
              | undefined;
            const imageUrl = tokens?.images?.hero ?? "";

            return (
              <NeonBlogPostCard
                key={post.id}
                id={post.id}
                title={
                  (locale === "en" ? post.title_en || post.title : post.title) ||
                  post.topic
                }
                subtitle={subtitle}
                niche={post.niche}
                imageUrl={imageUrl}
                createdAt={post.created_at}
                href={`/blog/${post.id}`}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}
