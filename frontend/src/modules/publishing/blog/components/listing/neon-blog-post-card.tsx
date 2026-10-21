import Link from "next/link";
import { NeonBadge } from "@/components/atoms/neon-badge";
import { NeonCard } from "@/components/molecules/neon-card";
import { TEXT, TEXT_MUTED, TEXT_DIM } from "@/constants/neon";
import { DEFAULT_LOCALE } from "@/i18n/config";
import { formatPublicDate } from "@/lib/public-blog-text";
import { PublicCoverImage } from "@/modules/publishing/blog/components/public-post/public-cover-image";
import type { NeonBlogPostCardComponentProps } from "./types";

export function NeonBlogPostCard({
  title,
  subtitle,
  niche,
  imageUrl,
  createdAt,
  href,
  featured,
  locale = DEFAULT_LOCALE,
}: Readonly<NeonBlogPostCardComponentProps>): React.ReactElement {
  const formattedDate = formatPublicDate(createdAt, locale);
  return (
    <Link href={href} className="block no-underline">
      <NeonCard hover padding={featured ? "lg" : "md"}>
        <PublicCoverImage
          src={imageUrl ?? ""}
          alt=""
          sizes="(max-width: 768px) 100vw, 400px"
          frameClassName="relative mb-3 rounded-md overflow-hidden"
          frameStyle={{ height: featured ? 160 : 100 }}
        />
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
        {formattedDate && (
          <time
            className="text-xs mt-2 block"
            style={{ color: TEXT_DIM }}
            dateTime={createdAt}
          >
            {formattedDate}
          </time>
        )}
      </NeonCard>
    </Link>
  );
}
