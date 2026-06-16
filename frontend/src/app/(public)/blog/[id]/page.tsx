import { notFound } from "next/navigation";
import { cookies } from "next/headers";
import { BLOG_LANGUAGES } from "@/constants/api";
import { designTokensToCssVars } from "@/constants/blog";
import { fetchBlogWithDesign } from "@/lib/server-fetch";
import { DEFAULT_LOCALE, SUPPORTED_LOCALES } from "@/i18n/config";
import type { SupportedLocale } from "@/i18n/config";
import {
  BackLink,
  BlogPostContent,
  BlogPostHeader,
  BlogPostHero,
} from "@/modules/publishing";

export const dynamic = "force-dynamic";

const BLOG_POST_MAX_WIDTH_PX = 768;

interface BlogPostPageProps {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ lang?: string }>;
}

export default async function PublicBlogPostPage({
  params,
  searchParams,
}: BlogPostPageProps) {
  const { id } = await params;
  const { lang: langParam } = await searchParams;

  const cookieStore = await cookies();
  const localeCookie = cookieStore.get("locale")?.value;
  const cookieLang: SupportedLocale =
    localeCookie && SUPPORTED_LOCALES.includes(localeCookie as SupportedLocale)
      ? (localeCookie as SupportedLocale)
      : DEFAULT_LOCALE;

  const currentLang =
    langParam === BLOG_LANGUAGES.ENGLISH ||
    langParam === BLOG_LANGUAGES.PORTUGUESE
      ? langParam
      : cookieLang;

  const data = await fetchBlogWithDesign(id, currentLang);

  if (!data) {
    notFound();
  }

  const { blog, design } = data;
  const cssVars = designTokensToCssVars(design);
  const badge = design.layout.badge_label;

  const heroImageUrl = design.images.hero ?? "";
  const slideImageUrls = design.images.slides;

  return (
    <div
      className="relative min-h-screen py-12"
      style={{
        background: design.colors.bg,
        fontFamily: design.typography.font_family_body,
        ...cssVars,
      }}
    >
      <div className="pointer-events-none fixed inset-0">
        <div
          className="absolute -top-24 right-0 h-96 w-96 rounded-full"
          style={{
            background: `radial-gradient(circle, ${design.colors.glow} 0%, transparent 70%)`,
          }}
        />
        <div
          className="absolute -bottom-24 left-0 h-80 w-80 rounded-full"
          style={{
            background: `radial-gradient(circle, ${design.colors.accent}0D 0%, transparent 70%)`,
          }}
        />
      </div>
      <div
        className="relative z-10 mx-auto px-6"
        style={{ maxWidth: `${BLOG_POST_MAX_WIDTH_PX + 432}px` }}
      >
        <BackLink />
        <article className="mx-auto max-w-3xl">
          <BlogPostHeader
            title={blog.title}
            subtitle={blog.subtitle ?? undefined}
            badge={badge}
            design={design}
          />
          {heroImageUrl && (
            <BlogPostHero
              imageUrl={heroImageUrl}
              title={blog.title}
              design={design}
            />
          )}
          <BlogPostContent
            markdown={blog.markdown}
            design={design}
            slideImages={slideImageUrls}
          />
        </article>
      </div>
    </div>
  );
}
