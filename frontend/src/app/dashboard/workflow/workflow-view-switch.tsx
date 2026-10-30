"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useRef } from "react";
import type { KeyboardEvent } from "react";
import {
  WORKFLOW_BOARD_ARCHIVED_PARAM,
  WORKFLOW_BOARD_ARCHIVED_VALUE,
} from "@/constants/workflow";
import type { WorkflowViewSwitchProps } from "./types";

const SEGMENT_CLASS =
  "rounded px-3 py-1.5 text-xs font-semibold transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-neon-cyan";

const SEGMENT_OFF_CLASS = `${SEGMENT_CLASS} text-white/70 hover:text-white`;
const SEGMENT_ON_CLASS = `${SEGMENT_CLASS} bg-neon-cyan/15 text-white`;

const NEXT_KEYS: ReadonlySet<string> = new Set(["ArrowRight", "ArrowDown"]);
const PREVIOUS_KEYS: ReadonlySet<string> = new Set(["ArrowLeft", "ArrowUp"]);

/**
 * The Ativos | Arquivados segmented control. A radiogroup whose state lives
 * in the URL (`?archived=1`), so Back and shared links restore the view; the
 * other query params are kept. Arrow keys move between the segments, select
 * and focus the checked one, with a single tab stop on it.
 */
export function WorkflowViewSwitch({
  archived,
}: Readonly<WorkflowViewSwitchProps>): React.ReactElement {
  const t = useTranslations("workflow");
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const activeRef = useRef<HTMLButtonElement | null>(null);
  const archivedRef = useRef<HTMLButtonElement | null>(null);

  function select(next: boolean): void {
    if (next === archived) return;
    const params = new URLSearchParams(searchParams.toString());
    if (next) {
      params.set(WORKFLOW_BOARD_ARCHIVED_PARAM, WORKFLOW_BOARD_ARCHIVED_VALUE);
    } else {
      params.delete(WORKFLOW_BOARD_ARCHIVED_PARAM);
    }
    const query = params.toString();
    router.replace(query === "" ? pathname : `${pathname}?${query}`, {
      scroll: false,
    });
    (next ? archivedRef : activeRef).current?.focus();
  }

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>): void {
    if (NEXT_KEYS.has(event.key)) {
      event.preventDefault();
      select(true);
      return;
    }
    if (PREVIOUS_KEYS.has(event.key)) {
      event.preventDefault();
      select(false);
    }
  }

  const segments = [
    { archived: false, label: t("archive.showActive"), ref: activeRef },
    { archived: true, label: t("archive.showArchived"), ref: archivedRef },
  ] as const;

  return (
    <div
      role="radiogroup"
      aria-label={t("board.viewGroup")}
      onKeyDown={onKeyDown}
      className="flex items-center rounded-md border border-[var(--color-neon-border-subtle)] p-0.5"
    >
      {segments.map((segment) => {
        const checked = segment.archived === archived;
        return (
          <button
            key={segment.label}
            ref={segment.ref}
            type="button"
            role="radio"
            aria-checked={checked}
            tabIndex={checked ? 0 : -1}
            onClick={() => select(segment.archived)}
            className={checked ? SEGMENT_ON_CLASS : SEGMENT_OFF_CLASS}
          >
            {segment.label}
          </button>
        );
      })}
    </div>
  );
}
