import type { KanbanCard, KanbanColumn } from "@/schemas/neon-kanban";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import { EDITORIAL_WORKFLOW_STATUS } from "@/constants/editorial-workflow";

export const BOARD_STATUS_FILTERS = [
  "all",
  "needsReview",
  "inProgress",
  "ready",
  "failed",
] as const;

export type BoardStatusFilter = (typeof BOARD_STATUS_FILTERS)[number];

export const BOARD_SORTS = ["updated", "title"] as const;

export type BoardSort = (typeof BOARD_SORTS)[number];

export interface BoardFilters {
  query: string;
  status: BoardStatusFilter;
  sort: BoardSort;
}

export const BOARD_FILTER_QUERY_PARAM = "q";
export const BOARD_FILTER_STATUS_PARAM = "status";
export const BOARD_FILTER_SORT_PARAM = "sort";

export const DEFAULT_BOARD_FILTERS: BoardFilters = {
  query: "",
  status: "all",
  sort: "updated",
};

const FILTER_BUCKETS: Record<string, BoardStatusFilter> = {
  [WORKFLOW_PHASE_STATUS.AWAITING_HUMAN]: "needsReview",
  [WORKFLOW_PHASE_STATUS.IN_PROGRESS]: "inProgress",
  [WORKFLOW_PHASE_STATUS.APPROVED]: "ready",
  [EDITORIAL_WORKFLOW_STATUS.APPROVED_FOR_PUBLISH]: "ready",
  [WORKFLOW_PHASE_STATUS.REJECTED]: "failed",
  [WORKFLOW_PHASE_STATUS.FAILED]: "failed",
};

/**
 * Case- and accent-insensitive comparison base: NFD decomposition with the
 * combining marks stripped, lowercased.
 */
export function normalizeBoardText(value: string): string {
  return value
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase();
}

/** The filter bucket a raw workflow status belongs to ("all" matches all). */
export function boardStatusBucket(status: string): BoardStatusFilter {
  return FILTER_BUCKETS[status] ?? "all";
}

function cardMatchesQuery(card: KanbanCard, query: string): boolean {
  if (query === "") return true;
  const needle = normalizeBoardText(query);
  return (
    normalizeBoardText(card.title).includes(needle) ||
    normalizeBoardText(card.description).includes(needle)
  );
}

function cardMatchesStatus(
  card: KanbanCard,
  status: BoardStatusFilter,
): boolean {
  if (status === "all") return true;
  return boardStatusBucket(card.statusKey) === status;
}

interface TitleSort {
  sort: BoardSort;
  locale: string | undefined;
}

function compareTitles(
  a: KanbanCard,
  b: KanbanCard,
  locale: string | undefined,
): number {
  const byTitle = a.title.localeCompare(b.title, locale);
  return byTitle !== 0 ? byTitle : a.id.localeCompare(b.id);
}

function compareUpdated(a: KanbanCard, b: KanbanCard): number {
  const aTime = a.updatedAt ?? null;
  const bTime = b.updatedAt ?? null;
  if (aTime === bTime) return a.id.localeCompare(b.id);
  if (aTime === null) return 1;
  if (bTime === null) return -1;
  return aTime < bTime ? 1 : -1;
}

function compareBySort(a: KanbanCard, b: KanbanCard, order: TitleSort): number {
  if (order.sort === "title") return compareTitles(a, b, order.locale);
  return compareUpdated(a, b);
}

/** Card counts per filter bucket, plus the total, over every column. */
export function countBoardStatusBuckets(
  columns: readonly KanbanColumn[],
): Record<BoardStatusFilter, number> {
  const counts: Record<BoardStatusFilter, number> = {
    all: 0,
    needsReview: 0,
    inProgress: 0,
    ready: 0,
    failed: 0,
  };
  for (const column of columns) {
    for (const card of column.cards) {
      counts.all += 1;
      const bucket = boardStatusBucket(card.statusKey);
      if (bucket === "all") continue;
      counts[bucket] += 1;
    }
  }
  return counts;
}

/**
 * Apply the toolbar to the localized board: query and status narrow the cards
 * (counts follow the filtered set) and the sort orders each column. Columns
 * without a match stay on the board as empty columns. The title sort uses the
 * dashboard locale and falls back to the id when titles are equal.
 */
export function filterBoardColumns(
  columns: readonly KanbanColumn[],
  filters: BoardFilters,
  locale?: string,
): KanbanColumn[] {
  const query = filters.query.trim();
  return columns.map((column) => {
    const cards = column.cards
      .filter((card) => cardMatchesQuery(card, query))
      .filter((card) => cardMatchesStatus(card, filters.status))
      .sort((a, b) => compareBySort(a, b, { sort: filters.sort, locale }));
    return { ...column, cards, count: cards.length };
  });
}

/**
 * Read the toolbar state from URL values; unknown or absent values fall back
 * to the defaults, and the defaults stay out of the URL.
 */
export function parseBoardFilters(input: {
  get: (name: string) => string | null;
}): BoardFilters {
  const status = input.get(BOARD_FILTER_STATUS_PARAM);
  const sort = input.get(BOARD_FILTER_SORT_PARAM);
  return {
    query: input.get(BOARD_FILTER_QUERY_PARAM) ?? "",
    status: (BOARD_STATUS_FILTERS as readonly string[]).includes(status ?? "")
      ? (status as BoardStatusFilter)
      : DEFAULT_BOARD_FILTERS.status,
    sort: (BOARD_SORTS as readonly string[]).includes(sort ?? "")
      ? (sort as BoardSort)
      : DEFAULT_BOARD_FILTERS.sort,
  };
}

/** `?q=…&status=…&sort=…` for the state; default values stay out of the URL. */
export function boardFiltersHref(
  pathname: string,
  filters: BoardFilters,
): string {
  const params = new URLSearchParams();
  if (filters.query !== "") {
    params.set(BOARD_FILTER_QUERY_PARAM, filters.query);
  }
  if (filters.status !== DEFAULT_BOARD_FILTERS.status) {
    params.set(BOARD_FILTER_STATUS_PARAM, filters.status);
  }
  if (filters.sort !== DEFAULT_BOARD_FILTERS.sort) {
    params.set(BOARD_FILTER_SORT_PARAM, filters.sort);
  }
  const query = params.toString();
  return query ? `${pathname}?${query}` : pathname;
}
