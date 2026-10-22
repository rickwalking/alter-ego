"use client";

import Image from "next/image";
import Link from "next/link";
import { useTranslations } from "next-intl";

import { useCarouselBlogPostHref } from "@/modules/publishing";
import type { CarouselProjectResponse } from "@/schemas/carousel";
import { PreviewSlides } from "./create-carousel-preview-slides";

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

/**
 * Falls back to the topic when the title is null, empty or whitespace (the
 * original `title || topic` intent; `??` would wrongly keep an empty title).
 */
function displayTitle(project: CarouselProjectResponse): string {
  return project.title?.trim() ? project.title : project.topic;
}

const TEMPLATE_VERSION_PREFIX = "v";

/** "v2" stays "v2" (the stored value may already carry the v). */
function formatTemplateVersion(version: string): string {
  return version.toLowerCase().startsWith(TEMPLATE_VERSION_PREFIX)
    ? version
    : `${TEMPLATE_VERSION_PREFIX}${version}`;
}

function PreviewHeader({
  project,
}: Readonly<CarouselPreviewProps>): React.ReactElement {
  return (
    <div className="p-4 space-y-3">
      <div className="flex items-center gap-2">
        <span className="rounded-full bg-[var(--color-primary)]/10 px-2 py-0.5 font-medium text-xs text-[var(--color-primary)]">
          {project.niche}
        </span>
        {project.template_version && (
          <span className="rounded-full bg-[var(--color-primary)]/10 px-2 py-0.5 font-medium text-xs text-[var(--color-primary)]">
            {formatTemplateVersion(project.template_version)}
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

function CreatorBadge({
  project,
}: Readonly<CarouselPreviewProps>): React.ReactElement {
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

/** Rendered slides when present, else the hero image, else nothing. */
function renderPreviewMedia({
  slideUrls,
  heroUrl,
  title,
}: Readonly<{
  slideUrls: string[] | null;
  heroUrl: string | null;
  title: string;
}>): React.ReactElement | null {
  if (slideUrls && slideUrls.length > 0) {
    return <PreviewSlides slideUrls={slideUrls} title={title} />;
  }
  if (!heroUrl) {
    return null;
  }
  return (
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
  );
}

export function CarouselPreview({
  project,
}: Readonly<CarouselPreviewProps>): React.ReactElement {
  const t = useTranslations("create");
  const slideUrls = extractRenderedSlides(project);
  const heroUrl = buildHeroImageUrl(project);
  const title = displayTitle(project);
  const { href: blogHref } = useCarouselBlogPostHref(project.id);

  return (
    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-background)] overflow-hidden">
      <PreviewHeader project={project} />

      {renderPreviewMedia({ slideUrls, heroUrl, title })}

      {Boolean(project.creator_name) && <CreatorBadge project={project} />}

      {project.caption && (
        <div className="px-4 py-3 border-t border-[var(--color-border)]">
          <p className="text-sm text-[var(--color-text-muted)] whitespace-pre-line">
            {project.caption}
          </p>
        </div>
      )}

      {blogHref ? (
        <div className="p-4 border-t border-[var(--color-border)]">
          <Link
            href={blogHref}
            className="inline-block rounded-md bg-[var(--color-primary)] px-4 py-2 font-medium text-sm text-[var(--color-text)] transition-colors hover:opacity-90"
          >
            {t("preview.viewBlog")}
          </Link>
        </div>
      ) : null}
    </div>
  );
}
