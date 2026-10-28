"use client";

import { useRef } from "react";
import { useTranslations } from "next-intl";
import { NeonSearchBar } from "@/components/molecules/neon-search-bar";
import { TEXT_DIM } from "@/constants/neon";
import {
  BOARD_SORTS,
  BOARD_STATUS_FILTERS,
  type BoardFilters,
  type BoardSort,
  type BoardStatusFilter,
} from "@/app/dashboard/workflow/board-filters";
import { useSearchShortcut } from "@/app/dashboard/workflow/use-board-filters";

const CHIP_CLASS =
  "rounded-full border border-transparent px-3 py-1 text-xs font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-bg-deep";
const CHIP_OFF_CLASS = `${CHIP_CLASS} border-[var(--color-neon-border-subtle)] text-white/70 hover:border-neon-cyan/50`;
const CHIP_ON_CLASS = `${CHIP_CLASS} bg-neon-cyan/15 border-neon-cyan/60 text-white`;
const SORT_CLASS =
  "rounded-md px-2 py-1 text-xs font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neon-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-bg-deep";

const CHIP_LABEL_KEYS: Record<BoardStatusFilter, string> = {
  all: "filters.all",
  needsReview: "filters.needsReview",
  inProgress: "filters.inProgress",
  ready: "filters.ready",
  failed: "filters.failed",
};

const SORT_LABEL_KEYS: Record<BoardSort, string> = {
  updated: "sort.updated",
  title: "sort.title",
};

export interface WorkflowToolbarProps {
  filters: BoardFilters;
  counts: Record<BoardStatusFilter, number>;
  onChange: (next: BoardFilters) => void;
}

/**
 * The board toolbar: search (title + topic), status filter chips with live
 * counts, and the sort order. Dumb and controlled; the state lives in the
 * URL through `useBoardFilters`.
 */
export function WorkflowToolbar({
  filters,
  counts,
  onChange,
}: Readonly<WorkflowToolbarProps>): React.ReactElement {
  const t = useTranslations("workflow.board");
  const searchRef = useRef<HTMLInputElement | null>(null);
  useSearchShortcut(searchRef);
  return (
    <div
      data-testid="workflow-toolbar"
      className="flex flex-wrap items-center gap-2"
      role="search"
    >
      <NeonSearchBar
        value={filters.query}
        onChange={(query) => onChange({ ...filters, query })}
        placeholder={t("searchPlaceholder")}
        ariaLabel={t("searchPlaceholder")}
        inputRef={searchRef}
        className="w-64"
      />
      <div className="flex flex-wrap items-center gap-1" role="group">
        {BOARD_STATUS_FILTERS.map((status) => (
          <button
            key={status}
            type="button"
            aria-pressed={filters.status === status}
            className={
              filters.status === status ? CHIP_ON_CLASS : CHIP_OFF_CLASS
            }
            onClick={() => onChange({ ...filters, status })}
          >
            {`${t(CHIP_LABEL_KEYS[status])} (${counts[status]})`}
          </button>
        ))}
      </div>
      <div
        className="flex items-center gap-1"
        role="radiogroup"
        aria-label={t("sort.label")}
      >
        <span className="text-xs" style={{ color: TEXT_DIM }}>
          {t("sort.label")}
        </span>
        {BOARD_SORTS.map((sort) => (
          <button
            key={sort}
            type="button"
            role="radio"
            aria-checked={filters.sort === sort}
            className={SORT_CLASS}
            style={{ color: filters.sort === sort ? undefined : TEXT_DIM }}
            onClick={() => onChange({ ...filters, sort })}
          >
            {t(SORT_LABEL_KEYS[sort])}
          </button>
        ))}
      </div>
    </div>
  );
}
