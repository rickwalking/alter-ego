import type { CarouselProjectResponse } from "@/schemas/carousel";
import type { NeonBlogPostCardProps } from "@/schemas/neon-blog-post-card";
import { toPublicCarouselImageUrl } from "@/lib/carousel-media-url";
import { truncate } from "@/lib/utils";

export function mapProjectToBlogPostCard(
  project: CarouselProjectResponse,
  locale: string,
): NeonBlogPostCardProps {
  const title =
    locale === "en"
      ? project.title_en || project.title || project.topic
      : project.title || project.topic;

  const subtitleRaw =
    locale === "en"
      ? project.subtitle_en || project.subtitle || project.topic
      : project.subtitle || project.topic;

  const rawImageUrl =
    project.design_tokens &&
    typeof project.design_tokens === "object" &&
    "images" in project.design_tokens &&
    project.design_tokens.images &&
    typeof project.design_tokens.images === "object" &&
    "hero" in project.design_tokens.images
      ? String((project.design_tokens.images as { hero?: string }).hero ?? "")
      : undefined;

  const imageUrl = rawImageUrl
    ? toPublicCarouselImageUrl(rawImageUrl)
    : undefined;

  return {
    id: project.id,
    title,
    subtitle: truncate(subtitleRaw ?? "", 120),
    niche: project.niche ?? undefined,
    imageUrl: imageUrl || undefined,
    createdAt: project.created_at,
    href: `/blog/${project.id}`,
  };
}
