import { notFound } from "next/navigation";
import { BLOG_LANGUAGES, DEFAULT_BLOG_LANGUAGE } from "@/constants/api";
import { designTokensToCssVars } from "@/constants/blog";
import { Container } from "@/components/layout";
import { fetchBlogWithDesign } from "@/lib/server-fetch";
import { BlogPostContent } from "./blog-post-content";
import { BlogPostHeader } from "./blog-post-header";
import { BlogPostHero } from "./blog-post-hero";
import { BackLink } from "./back-link";

interface BlogPostPageProps {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ lang?: string }>;
}

export default async function BlogPostPage({ params, searchParams }: BlogPostPageProps) {
  const { id } = await params;
  const { lang: langParam } = await searchParams;
  const currentLang = langParam === BLOG_LANGUAGES.ENGLISH ? BLOG_LANGUAGES.ENGLISH : DEFAULT_BLOG_LANGUAGE;
  const data = await fetchBlogWithDesign(id, currentLang);

  if (!data) {
    notFound();
  }

  const { blog, design } = data;
  const cssVars = designTokensToCssVars(design);
  const badge = design.layout.badge_label;
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const heroImageUrl = design.images.hero
    ? `${apiBaseUrl}${design.images.hero}`
    : "";
  const slideImageUrls = design.images.slides.map(
    (path) => `${apiBaseUrl}${path}`
  );
  const blogPath = `/blog/${id}`;

  return (
    <div
      className="min-h-screen"
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
      <Container className="relative z-10 py-12">
        <BackLink />
        <article className="mx-auto max-w-3xl">
          <BlogPostHeader
            title={blog.title}
            subtitle={blog.subtitle ?? undefined}
            badge={badge}
            design={design}
            currentLang={currentLang}
            availableLanguages={blog.available_languages}
            blogPath={blogPath}
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
      </Container>
    </div>
  );
}
