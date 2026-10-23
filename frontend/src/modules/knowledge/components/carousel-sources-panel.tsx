"use client";

import { useState } from "react";
import Link from "next/link";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { ExternalLink, Layers } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";

import { NeonBadge } from "@/components/atoms/neon-badge";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonLabel } from "@/components/atoms/neon-label";
import { ROUTE_PATHS } from "@/constants/api";
import {
  ALL_CAROUSELS,
  CAROUSEL_SOURCES_PAGE_SIZE,
  KNOWN_SOURCE_TYPES,
} from "@/constants/knowledge-sources";
import { formatDate } from "@/lib/utils";
import { carouselSourcesOptions } from "../queries";
import type {
  CarouselFilterProps,
  CarouselSourceRowProps,
  SourcesPagerProps,
} from "./types";

/** A source type in words, or the raw type when it has no label. */
function useSourceTypeLabel(): (sourceType: string) => string {
  const t = useTranslations("knowledge.carouselSources.types");
  return (sourceType) =>
    KNOWN_SOURCE_TYPES.includes(sourceType) ? t(sourceType) : sourceType;
}

/** One read-only source: title, type, date, its URL and its carousel. */
function CarouselSourceRow({
  source,
}: Readonly<CarouselSourceRowProps>): React.ReactElement {
  const t = useTranslations("knowledge.carouselSources");
  const locale = useLocale();
  const typeLabel = useSourceTypeLabel();
  return (
    <li className="flex flex-col gap-1 rounded-lg border border-[var(--color-border)] p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-medium">{source.title}</span>
        <NeonBadge variant="secondary" className="text-xs">
          {typeLabel(source.source_type)}
        </NeonBadge>
        <span className="text-xs text-[var(--color-muted-foreground)]">
          {formatDate(source.created_at, locale)}
        </span>
      </div>
      {source.url && (
        <a
          href={source.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 truncate text-sm text-[var(--color-primary)] hover:underline"
        >
          <ExternalLink className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
          {source.url}
        </a>
      )}
      <Link
        href={ROUTE_PATHS.CREATE_WORKSPACE(source.project_id)}
        aria-label={t("openCarousel", { title: source.project_title })}
        className="inline-flex items-center gap-1 text-sm text-[var(--color-muted-foreground)] hover:text-[var(--color-primary)]"
      >
        <Layers className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        {source.project_title}
      </Link>
    </li>
  );
}

/** The carousel filter, listing each carousel with its source count. */
function CarouselFilter({
  carousels,
  value,
  onChange,
}: Readonly<CarouselFilterProps>): React.ReactElement {
  const t = useTranslations("knowledge.carouselSources");
  return (
    <div className="flex items-center gap-2">
      <NeonLabel htmlFor="carousel-sources-filter">{t("filter")}</NeonLabel>
      <select
        id="carousel-sources-filter"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="rounded-md border border-[var(--color-border)] bg-transparent px-2 py-1.5 text-sm"
      >
        <option value={ALL_CAROUSELS}>{t("allCarousels")}</option>
        {carousels.map((carousel) => (
          <option key={carousel.project_id} value={carousel.project_id}>
            {`${carousel.title} (${carousel.count})`}
          </option>
        ))}
      </select>
    </div>
  );
}

/** "x–y de N" with previous / next. */
function SourcesPager({
  offset,
  shown,
  total,
  onOffsetChange,
}: Readonly<SourcesPagerProps>): React.ReactElement {
  const t = useTranslations("knowledge.carouselSources");
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 text-sm">
      <span aria-live="polite">
        {t("range", { from: offset + 1, to: offset + shown, total })}
      </span>
      <div className="flex gap-2">
        <NeonButton
          variant="outline"
          disabled={offset === 0}
          onClick={() =>
            onOffsetChange(Math.max(0, offset - CAROUSEL_SOURCES_PAGE_SIZE))
          }
        >
          {t("previous")}
        </NeonButton>
        <NeonButton
          variant="outline"
          disabled={offset + shown >= total}
          onClick={() => onOffsetChange(offset + CAROUSEL_SOURCES_PAGE_SIZE)}
        >
          {t("next")}
        </NeonButton>
      </div>
    </div>
  );
}

/** Read-only list of the caller's carousel sources, paged and filterable. */
export function CarouselSourcesPanel(): React.ReactElement {
  const t = useTranslations("knowledge.carouselSources");
  const [offset, setOffset] = useState(0);
  const [projectId, setProjectId] = useState(ALL_CAROUSELS);
  const { data, isError } = useQuery({
    ...carouselSourcesOptions(offset, projectId),
    placeholderData: keepPreviousData,
  });
  const choose = (next: string): void => {
    setProjectId(next);
    setOffset(0);
  };

  if (isError) {
    return (
      <p
        role="alert"
        className="py-12 text-center text-[var(--color-destructive)]"
      >
        {t("error")}
      </p>
    );
  }
  if (!data) {
    return (
      <p
        role="status"
        className="py-12 text-center text-[var(--color-muted-foreground)]"
      >
        {t("loading")}
      </p>
    );
  }
  if (data.total === 0 && projectId === ALL_CAROUSELS) {
    return (
      <div className="space-y-2 py-12 text-center text-[var(--color-muted-foreground)]">
        <p>{t("empty")}</p>
        <p className="text-sm">{t("emptyHint")}</p>
      </div>
    );
  }
  return (
    <section aria-label={t("list")} className="space-y-4">
      <CarouselFilter
        carousels={data.carousels}
        value={projectId}
        onChange={choose}
      />
      <ul className="space-y-3">
        {data.items.map((source) => (
          <CarouselSourceRow key={source.id} source={source} />
        ))}
      </ul>
      {data.total > 0 && (
        <SourcesPager
          offset={data.offset}
          shown={data.items.length}
          total={data.total}
          onOffsetChange={setOffset}
        />
      )}
    </section>
  );
}
