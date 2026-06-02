import { useState, useCallback, useRef } from "react";
import Image from "next/image";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { ROUTE_PATHS } from "@/constants/api";
import type { CarouselProjectResponse } from "@/schemas/carousel";

interface CarouselPreviewProps {
  project: CarouselProjectResponse;
}

function extractRenderedSlides(
  project: CarouselProjectResponse,
): string[] | null {
  const tokens = project.design_tokens as
    | {
        images?: {
          rendered_slides_pt?: string[] | null;
          rendered_slides_en?: string[] | null;
          slides?: string[] | null;
        } | null;
      }
    | null
    | undefined;
  const rendered =
    tokens?.images?.rendered_slides_pt ?? tokens?.images?.rendered_slides_en;
  if (rendered && rendered.length > 0) return rendered;
  const rawSlides = tokens?.images?.slides;
  if (rawSlides && rawSlides.length > 0) return rawSlides;
  return null;
}

function buildHeroImageUrl(project: CarouselProjectResponse): string | null {
  const tokens = project.design_tokens as
    | { images?: { hero?: string } }
    | null
    | undefined;
  return tokens?.images?.hero ?? null;
}

export function CarouselPreview({
  project,
}: CarouselPreviewProps): React.ReactElement {
  const t = useTranslations("create");
  const [activeIndex, setActiveIndex] = useState(0);
  const viewportRef = useRef<HTMLDivElement>(null);
  const slideUrls = extractRenderedSlides(project);
  const heroUrl = buildHeroImageUrl(project);

  const scrollToIndex = useCallback(
    (index: number): void => {
      const viewport = viewportRef.current;
      if (!viewport || !slideUrls) return;
      const clamped = Math.max(0, Math.min(index, slideUrls.length - 1));
      viewport.scrollTo({
        left: clamped * viewport.clientWidth,
        behavior: "smooth",
      });
    },
    [slideUrls],
  );

  const handleScroll = useCallback(
    (event: React.UIEvent<HTMLDivElement>): void => {
      const target = event.currentTarget;
      const index = Math.round(target.scrollLeft / target.clientWidth);
      if (index !== activeIndex) {
        setActiveIndex(index);
      }
    },
    [activeIndex],
  );

  const goPrev = useCallback((): void => {
    if (!slideUrls) return;
    const newIndex = Math.max(0, activeIndex - 1);
    setActiveIndex(newIndex);
    scrollToIndex(newIndex);
  }, [activeIndex, slideUrls, scrollToIndex]);

  const goNext = useCallback((): void => {
    if (!slideUrls) return;
    const newIndex = Math.min((slideUrls?.length ?? 1) - 1, activeIndex + 1);
    setActiveIndex(newIndex);
    scrollToIndex(newIndex);
  }, [activeIndex, slideUrls, scrollToIndex]);

  const hasCreator = Boolean(project.creator_name);

  return (
    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-background)] overflow-hidden">
      {/* Header */}
      <div className="p-4 space-y-3">
        <div className="flex items-center gap-2">
          <span className="rounded-full bg-[var(--color-primary)]/10 px-2 py-0.5 font-medium text-xs text-[var(--color-primary)]">
            {project.niche}
          </span>
          {project.template_version && (
            <span className="rounded-full bg-[var(--color-primary)]/10 px-2 py-0.5 font-medium text-xs text-[var(--color-primary)]">
              v{project.template_version}
            </span>
          )}
        </div>
        <h3 className="font-semibold text-lg">
          {project.title || project.topic}
        </h3>
        {project.subtitle && (
          <p className="text-[var(--color-text-muted)] text-sm">
            {project.subtitle}
          </p>
        )}
      </div>

      {/* Slide viewer */}
      {slideUrls && slideUrls.length > 0 ? (
        <div className="relative">
          <div
            ref={viewportRef}
            onScroll={handleScroll}
            className="flex snap-x snap-mandatory overflow-x-auto"
            style={{ scrollbarWidth: "none" }}
          >
            {slideUrls.map((url, i) => (
              <div
                key={`slide-${i + 1}`}
                className="relative aspect-[4/5] w-full flex-shrink-0 snap-center"
              >
                <Image
                  src={url}
                  alt={`${project.title || project.topic} – slide ${i + 1}`}
                  fill
                  className="object-cover"
                  sizes="(min-width: 1024px) 33vw, 100vw"
                  unoptimized
                />
                <div className="absolute top-3 right-3 rounded-full bg-background/60 px-2 py-0.5 text-foreground text-xs">
                  {i + 1} / {slideUrls.length}
                </div>
              </div>
            ))}
          </div>

          {slideUrls.length > 1 && (
            <>
              <button
                type="button"
                onClick={goPrev}
                disabled={activeIndex === 0}
                aria-label={t("preview.previousSlide")}
                className="absolute left-2 top-1/2 -translate-y-1/2 rounded-full bg-background/50 p-2 text-foreground transition-opacity hover:bg-background/70 disabled:opacity-0"
              >
                <ChevronLeft className="h-5 w-5" />
              </button>
              <button
                type="button"
                onClick={goNext}
                disabled={activeIndex === slideUrls.length - 1}
                aria-label={t("preview.nextSlide")}
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded-full bg-background/50 p-2 text-foreground transition-opacity hover:bg-background/70 disabled:opacity-0"
              >
                <ChevronRight className="h-5 w-5" />
              </button>
            </>
          )}
        </div>
      ) : heroUrl ? (
        <div className="relative aspect-[4/3] w-full overflow-hidden">
          <Image
            src={heroUrl}
            alt={project.title || project.topic}
            fill
            className="object-cover"
            sizes="(min-width: 1024px) 33vw, 100vw"
            unoptimized
          />
        </div>
      ) : null}

      {/* Creator watermark */}
      {hasCreator && (
        <div className="px-4 py-3 flex items-center gap-3 border-t border-[var(--color-border)]">
          {project.creator_avatar_url && (
            <div className="relative w-8 h-8 rounded-full overflow-hidden border border-[var(--color-primary)]">
              <Image
                src={project.creator_avatar_url}
                alt={project.creator_name || ""}
                fill
                className="object-cover"
                unoptimized
              />
            </div>
          )}
          <div className="flex flex-col">
            <span className="text-sm font-semibold text-[var(--color-text)]">
              {project.creator_name}
            </span>
            {project.creator_handle && (
              <span className="text-xs text-[var(--color-text-muted)] font-mono">
                @{project.creator_handle}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Caption */}
      {project.caption && (
        <div className="px-4 py-3 border-t border-[var(--color-border)]">
          <p className="text-sm text-[var(--color-text-muted)] whitespace-pre-line">
            {project.caption || ""}
          </p>
        </div>
      )}

      {/* Actions */}
      <div className="p-4 border-t border-[var(--color-border)]">
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
