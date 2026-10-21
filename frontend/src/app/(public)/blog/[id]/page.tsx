import { cache } from "react";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations } from "next-intl/server";
import { BLOG_LANGUAGES } from "@/constants/api";
import { designTokensToCssVars } from "@/constants/blog";
import { resolvePublicBlogView } from "@/lib/public-blog";
import { toCategoryLabel } from "@/lib/public-blog-text";
import { getRequestLocale } from "@/i18n/request-locale";
import {
  BackLink,
  BlogLanguageSwitch,
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

const META_DESCRIPTION_MAX_CHARS = 160;
const META_TITLE_SEPARATOR = " · ";

/** One backend round-trip per request for both the page and its metadata. */
const loadView = cache(resolvePublicBlogView);

async function resolveLang(langParam: string | undefined): Promise<string> {
  if (
    langParam === BLOG_LANGUAGES.ENGLISH ||
    langParam === BLOG_LANGUAGES.PORTUGUESE
  ) {
    return langParam;
  }
  return getRequestLocale();
}

function truncateDescription(text: string): string {
  if (text.length <= META_DESCRIPTION_MAX_CHARS) return text;
  return `${text.slice(0, META_DESCRIPTION_MAX_CHARS - 1).trimEnd()}…`;
}

/**
 * Per-post title/description instead of the generic site title.
 *
 * The OG image is the post's own cover only, never a carousel slide.
 */
export async function generateMetadata({
  params,
  searchParams,
}: BlogPostPageProps): Promise<Metadata> {
  const { id } = await params;
  const { lang } = await searchParams;
  const view = await loadView(id, await resolveLang(lang));
  if (!view) {
    return {};
  }
  const t = await getTranslations("blog");
  const title = `${view.title || t("untitledPost")}${META_TITLE_SEPARATOR}${t("metaTitleSuffix")}`;
  const description = view.subtitle
    ? truncateDescription(view.subtitle)
    : undefined;
  const image = view.cover?.url;
  return {
    title,
    description,
    openGraph: {
      title,
      description,
      type: "article",
      images: image ? [image] : undefined,
    },
  };
}

export default async function PublicBlogPostPage({
  params,
  searchParams,
}: Readonly<BlogPostPageProps>) {
  const { id } = await params;
  const { lang: langParam } = await searchParams;
  const currentLang = await resolveLang(langParam);
  const t = await getTranslations("blog");

  const view = await loadView(id, currentLang);

  if (!view) {
    notFound();
  }

  const { design } = view;
  const cssVars = designTokensToCssVars(design);
  const badge = toCategoryLabel(design.layout.badge_label);
  const title = view.title || t("untitledPost");

  const languageOptions = [
    {
      language: BLOG_LANGUAGES.PORTUGUESE,
      label: t("contentLanguagePt"),
      href: `?lang=${BLOG_LANGUAGES.PORTUGUESE}`,
    },
    {
      language: BLOG_LANGUAGES.ENGLISH,
      label: t("contentLanguageEn"),
      href: `?lang=${BLOG_LANGUAGES.ENGLISH}`,
    },
  ];

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
        className="relative z-10 mx-auto px-4 sm:px-6"
        style={{ maxWidth: `${BLOG_POST_MAX_WIDTH_PX + 432}px` }}
      >
        <BackLink />
        <article className="mx-auto max-w-3xl">
          <BlogPostHeader
            title={title}
            subtitle={view.subtitle ?? undefined}
            badge={badge}
            swipeHint={t("swipeHint")}
            design={design}
          />
          <BlogLanguageSwitch
            activeLanguage={currentLang}
            label={t("contentLanguage")}
            options={languageOptions}
          />
          <BlogPostHero cover={view.cover} design={design} />
          <BlogPostContent sections={view.sections} design={design} />
        </article>
      </div>
    </div>
  );
}
