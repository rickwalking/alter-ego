import Link from "next/link";
import { NeonBadge } from "@/components/atoms/neon-badge";
import { NeonCard } from "@/components/molecules/neon-card";
import { TEXT, TEXT_MUTED, TEXT_DIM } from "@/constants/neon";
import type { NeonBlogPostCardProps } from "@/schemas/neon-blog-post-card";

export interface NeonBlogPostCardComponentProps extends NeonBlogPostCardProps {
  featured?: boolean;
}

export function NeonBlogPostCard({
  title,
  subtitle,
  niche,
  imageUrl,
  createdAt,
  href,
  featured,
}: NeonBlogPostCardComponentProps): React.ReactElement {
  return (
    <Link href={href} className="block no-underline">
      <NeonCard hover padding={featured ? "lg" : "md"}>
        {imageUrl && (
          <div
            className="mb-3 rounded-md overflow-hidden"
            style={{ height: featured ? 160 : 100 }}
          >
            <img src={imageUrl} alt="" className="w-full h-full object-cover" />
          </div>
        )}
        {niche && (
          <NeonBadge variant="magenta" className="mb-2">
            {niche}
          </NeonBadge>
        )}
        <h3
          className={`font-bold tracking-tight ${featured ? "text-lg" : "text-sm"}`}
          style={{ color: TEXT }}
        >
          {title}
        </h3>
        {subtitle && (
          <p
            className="text-sm mt-1 line-clamp-2"
            style={{ color: TEXT_MUTED }}
          >
            {subtitle}
          </p>
        )}
        <time
          className="text-xs mt-2 block"
          style={{ color: TEXT_DIM }}
          dateTime={createdAt}
        >
          {new Date(createdAt).toLocaleDateString()}
        </time>
      </NeonCard>
    </Link>
  );
}
