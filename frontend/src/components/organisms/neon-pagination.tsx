"use client";

import { NeonButton } from "@/components/atoms/neon-button";

export interface NeonPaginationProps {
  total: number;
  page: number;
  pageSize?: number;
  onPageChange?: (page: number) => void;
}

export function NeonPagination({
  total,
  page,
  pageSize = 10,
  onPageChange,
}: NeonPaginationProps): React.ReactElement {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const canPrev = page > 1;
  const canNext = page < totalPages;

  return (
    <div className="flex items-center justify-center gap-2 mt-6">
      <NeonButton
        variant="secondary"
        size="sm"
        disabled={!canPrev}
        onClick={() => onPageChange?.(page - 1)}
      >
        Previous
      </NeonButton>
      <span className="text-sm text-text-muted px-2">
        {page} / {totalPages}
      </span>
      <NeonButton
        variant="secondary"
        size="sm"
        disabled={!canNext}
        onClick={() => onPageChange?.(page + 1)}
      >
        Next
      </NeonButton>
    </div>
  );
}
