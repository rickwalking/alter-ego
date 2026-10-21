import { PublicCoverImage } from "./public-cover-image";
import type { BlogPostHeroProps } from "./types";

const HERO_FRAME_CLASS =
  "relative mb-10 h-72 w-full overflow-hidden rounded-2xl md:h-96";

/**
 * Article hero: the post's own cover with its stored alt (ADR-0025),
 * or a neutral themed default when the cover is null — never a carousel slide.
 */
export function BlogPostHero({ cover, design }: Readonly<BlogPostHeroProps>) {
  const { colors } = design;
  const frameStyle = {
    border: `1px solid ${colors.primary}33`,
    boxShadow: `0 0 60px ${colors.primary}1F, 0 20px 40px rgba(0,0,0,0.4)`,
  };

  if (!cover) {
    return (
      <div
        data-testid="blog-hero-fallback"
        aria-hidden="true"
        className={HERO_FRAME_CLASS}
        style={{
          ...frameStyle,
          background: `linear-gradient(135deg, ${colors.primary}33 0%, ${colors.accent}1A 50%, ${colors.bg} 100%)`,
        }}
      />
    );
  }

  return (
    <PublicCoverImage
      src={cover.url}
      alt={cover.alt}
      sizes="(max-width: 768px) 100vw, 768px"
      frameClassName={HERO_FRAME_CLASS}
      frameStyle={frameStyle}
      overlay={
        <div
          className="absolute inset-0"
          style={{
            background: `linear-gradient(to bottom, transparent 40%, ${colors.bg} 100%)`,
          }}
        />
      }
    />
  );
}
