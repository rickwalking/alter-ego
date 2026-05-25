import Link from "next/link";
import Image from "next/image";
import { useTranslations } from "next-intl";
import { ROUTE_PATHS } from "@/constants/api";
import type { CarouselProjectResponse } from "@/schemas/carousel";

interface CarouselPreviewProps {
  project: CarouselProjectResponse;
}

function buildHeroImageUrl(project: CarouselProjectResponse): string | null {
  // `design_tokens.images.hero` is already a full API path
  // (e.g. `/api/carousels/<id>/images/slide_1`). Prepend the API base
  // when one is configured and hand it to <img> as-is.
  const tokens = project.design_tokens as
    | { images?: { hero?: string } }
    | null
    | undefined;
  const heroPath = tokens?.images?.hero;
  if (!heroPath) return null;
  return heroPath;
}

export function CarouselPreview({ project }: CarouselPreviewProps) {
  const t = useTranslations("create");
  const imageUrl = buildHeroImageUrl(project);

  return (
    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-background)] overflow-hidden">
      {imageUrl && (
        <div className="relative aspect-[4/3] w-full overflow-hidden">
          <Image
            src={imageUrl}
            alt={project.title || project.topic}
            fill
            className="object-cover"
            sizes="(min-width: 1024px) 33vw, 100vw"
            unoptimized
          />
        </div>
      )}
      <div className="p-4 space-y-3">
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-[var(--color-primary)]/10 px-2 py-0.5 font-medium text-xs text-[var(--color-primary)]">
            {project.niche}
          </span>
        </div>
        <h3 className="font-semibold text-lg">
          {project.title || project.topic}
        </h3>
        {project.subtitle && (
          <p className="text-[var(--color-text-muted)] text-sm">
            {project.subtitle}
          </p>
        )}
        <Link
          href={ROUTE_PATHS.BLOG_POST(project.id)}
          className="inline-block rounded-md bg-[var(--color-primary)] px-4 py-2 font-medium text-sm text-[var(--color-text)] transition-colors hover:opacity-90"
        >
          {t("preview.viewBlog")}
        </Link>
      </div>
    </div>
  );
}
