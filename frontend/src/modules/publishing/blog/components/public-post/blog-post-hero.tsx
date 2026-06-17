import Image from "next/image";
import type { BlogPostHeroProps } from "./types";

export function BlogPostHero({ imageUrl, title, design }: BlogPostHeroProps) {
  const { colors } = design;

  return (
    <div
      className="relative mb-10 h-72 w-full overflow-hidden rounded-2xl md:h-96"
      style={{
        border: `1px solid ${colors.primary}33`,
        boxShadow: `0 0 60px ${colors.primary}1F, 0 20px 40px rgba(0,0,0,0.4)`,
      }}
    >
      <Image
        src={imageUrl}
        alt={title}
        fill
        sizes="(max-width: 768px) 100vw, 768px"
        className="object-cover"
        unoptimized
      />
      <div
        className="absolute inset-0"
        style={{
          background: `linear-gradient(to bottom, transparent 40%, ${colors.bg} 100%)`,
        }}
      />
    </div>
  );
}
