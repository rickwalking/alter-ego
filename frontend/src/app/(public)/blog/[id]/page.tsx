import { notFound } from "next/navigation";
import { getRequestLocale } from "@/i18n/request-locale";
import { BLOG_LANGUAGES } from "@/constants/api";
import { designTokensToCssVars } from "@/constants/blog";
import { resolvePublicBlogView } from "@/lib/public-blog";
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

  const cookieLang = await getRequestLocale();

  const currentLang =
    langParam === BLOG_LANGUAGES.ENGLISH ||
    langParam === BLOG_LANGUAGES.PORTUGUESE
      ? langParam
      : cookieLang;

  const view = await resolvePublicBlogView(id, currentLang);

  if (!view) {
    notFound();
  }

  const { design } = view;
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
            title={view.title}
            subtitle={view.subtitle ?? undefined}
            badge={badge}
            design={design}
          />
          {heroImageUrl && (
            <BlogPostHero
              imageUrl={heroImageUrl}
              title={view.title}
              design={design}
            />
          )}
          <BlogPostContent
            markdown={view.markdown}
            design={design}
            slideImages={slideImageUrls}
          />
        </article>
      </div>
    </div>
  );
}
