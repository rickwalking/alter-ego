"use client";

import { useCallback, useRef, useState } from "react";
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
  const images = (
    project.design_tokens as
      | {
          images?: {
            rendered_slides_pt?: string[] | null;
            rendered_slides_en?: string[] | null;
            slides?: string[] | null;
          } | null;
        }
      | null
      | undefined
  )?.images;
  const rendered = images?.rendered_slides_pt ?? images?.rendered_slides_en;
  if (rendered?.length) return rendered;
  const rawSlides = images?.slides;
  if (rawSlides?.length) return rawSlides;
  return null;
}

function buildHeroImageUrl(project: CarouselProjectResponse): string | null {
  const tokens = project.design_tokens as
    | { images?: { hero?: string } }
    | null
    | undefined;
  return tokens?.images?.hero ?? null;
}

function displayTitle(project: CarouselProjectResponse): string {
  // Fall back to the topic when the title is null/empty/whitespace (the original
  // `title || topic` intent — `??` would wrongly keep an empty-string title).
  return project.title?.trim() ? project.title : project.topic;
}

interface SlideViewport {
  activeIndex: number;
  viewportRef: React.RefObject<HTMLDivElement | null>;
  handleScroll: (event: React.UIEvent<HTMLDivElement>) => void;
  goPrev: () => void;
  goNext: () => void;
}

function useSlideViewport(slideUrls: string[]): SlideViewport {
  const [activeIndex, setActiveIndex] = useState(0);
  const viewportRef = useRef<HTMLDivElement>(null);

  const scrollToIndex = useCallback(
    (index: number): void => {
      const viewport = viewportRef.current;
      if (!viewport) return;
      const clamped = Math.max(0, Math.min(index, slideUrls.length - 1));
      viewport.scrollTo({
        left: clamped * viewport.clientWidth,
        behavior: "smooth",
      });
    },
    [slideUrls.length],
  );

  const handleScroll = useCallback(
    (event: React.UIEvent<HTMLDivElement>): void => {
      const target = event.currentTarget;
      const index = Math.round(target.scrollLeft / target.clientWidth);
      if (index !== activeIndex) setActiveIndex(index);
    },
    [activeIndex],
  );

  const goPrev = useCallback((): void => {
    const newIndex = Math.max(0, activeIndex - 1);
    setActiveIndex(newIndex);
    scrollToIndex(newIndex);
  }, [activeIndex, scrollToIndex]);

  const goNext = useCallback((): void => {
    const newIndex = Math.min(slideUrls.length - 1, activeIndex + 1);
    setActiveIndex(newIndex);
    scrollToIndex(newIndex);
  }, [activeIndex, slideUrls.length, scrollToIndex]);

  return { activeIndex, viewportRef, handleScroll, goPrev, goNext };
}

function SlideNav({
  activeIndex,
  count,
  onPrev,
  onNext,
}: {
  activeIndex: number;
  count: number;
  onPrev: () => void;
  onNext: () => void;
}): React.ReactElement {
  const t = useTranslations("create");
  return (
    <>
      <button
        type="button"
        onClick={onPrev}
        disabled={activeIndex === 0}
        aria-label={t("preview.previousSlide")}
        className="absolute left-2 top-1/2 -translate-y-1/2 rounded-full bg-background/50 p-2 text-foreground transition-opacity hover:bg-background/70 disabled:opacity-0"
      >
        <ChevronLeft className="h-5 w-5" />
      </button>
      <button
        type="button"
        onClick={onNext}
        disabled={activeIndex === count - 1}
        aria-label={t("preview.nextSlide")}
        className="absolute right-2 top-1/2 -translate-y-1/2 rounded-full bg-background/50 p-2 text-foreground transition-opacity hover:bg-background/70 disabled:opacity-0"
      >
        <ChevronRight className="h-5 w-5" />
      </button>
    </>
  );
}

function PreviewSlides({
  slideUrls,
  title,
}: {
  slideUrls: string[];
  title: string;
}): React.ReactElement {
  const { activeIndex, viewportRef, handleScroll, goPrev, goNext } =
    useSlideViewport(slideUrls);
  return (
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
              alt={`${title} – slide ${i + 1}`}
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
        <SlideNav
          activeIndex={activeIndex}
          count={slideUrls.length}
          onPrev={goPrev}
          onNext={goNext}
        />
      )}
    </div>
  );
}

function PreviewHeader({ project }: CarouselPreviewProps): React.ReactElement {
  return (
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
      <h3 className="font-semibold text-lg">{displayTitle(project)}</h3>
      {project.subtitle && (
        <p className="text-[var(--color-text-muted)] text-sm">
          {project.subtitle}
        </p>
      )}
    </div>
  );
}

function CreatorBadge({ project }: CarouselPreviewProps): React.ReactElement {
  return (
    <div className="px-4 py-3 flex items-center gap-3 border-t border-[var(--color-border)]">
      {project.creator_avatar_url && (
        <div className="relative w-8 h-8 rounded-full overflow-hidden border border-[var(--color-primary)]">
          <Image
            src={project.creator_avatar_url}
            alt={project.creator_name ?? ""}
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
  );
}

export function CarouselPreview({
  project,
}: CarouselPreviewProps): React.ReactElement {
  const t = useTranslations("create");
  const slideUrls = extractRenderedSlides(project);
  const heroUrl = buildHeroImageUrl(project);
  const title = displayTitle(project);

  return (
    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-background)] overflow-hidden">
      <PreviewHeader project={project} />

      {slideUrls && slideUrls.length > 0 ? (
        <PreviewSlides slideUrls={slideUrls} title={title} />
      ) : heroUrl ? (
        <div className="relative aspect-[4/3] w-full overflow-hidden">
          <Image
            src={heroUrl}
            alt={title}
            fill
            className="object-cover"
            sizes="(min-width: 1024px) 33vw, 100vw"
            unoptimized
          />
        </div>
      ) : null}

      {Boolean(project.creator_name) && <CreatorBadge project={project} />}

      {project.caption && (
        <div className="px-4 py-3 border-t border-[var(--color-border)]">
          <p className="text-sm text-[var(--color-text-muted)] whitespace-pre-line">
            {project.caption}
          </p>
        </div>
      )}

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
