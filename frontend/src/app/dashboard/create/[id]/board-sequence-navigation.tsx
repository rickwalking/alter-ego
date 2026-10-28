"use client";

import { useEffect, useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";
import { TEXT_MUTED } from "@/constants/neon";
import {
  boardSequenceSnapshot,
  type BoardSequence,
} from "@/modules/editorial-operations";

const PREVIOUS_KEY = "[";
const NEXT_KEY = "]";
const EDITABLE_TAGS: ReadonlySet<string> = new Set([
  "INPUT",
  "TEXTAREA",
  "SELECT",
]);

interface BoardSequenceNavigationProps {
  projectId: string;
}

function adjacentId(
  ids: string[],
  index: number,
  offset: number,
): string | null {
  return ids[index + offset] ?? null;
}

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return EDITABLE_TAGS.has(target.tagName) || target.isContentEditable;
}

function isModifierEvent(event: KeyboardEvent): boolean {
  return event.metaKey || event.ctrlKey || event.altKey;
}

function subscribeToStorage(onChange: () => void): () => void {
  window.addEventListener("storage", onChange);
  return () => window.removeEventListener("storage", onChange);
}

function useSequenceShortcuts(
  previousId: string | null,
  nextId: string | null,
): void {
  const router = useRouter();
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent): void => {
      if (event.defaultPrevented || isModifierEvent(event)) return;
      if (isEditableTarget(event.target)) return;
      let id: string | null = null;
      if (event.key === PREVIOUS_KEY) id = previousId;
      if (event.key === NEXT_KEY) id = nextId;
      if (id === null) return;
      event.preventDefault();
      router.push(DASHBOARD_ROUTES.CREATE_WORKSPACE(id));
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [nextId, previousId, router]);
}

/**
 * Navigate the ordered board column that led to this carousel workspace. The
 * stored sequence is read through `useSyncExternalStore` with a null server
 * snapshot, so the server render and hydration stay consistent without
 * deferring state.
 */
export function BoardSequenceNavigation({
  projectId,
}: Readonly<BoardSequenceNavigationProps>): React.ReactElement | null {
  const t = useTranslations("create.boardSequence");
  const router = useRouter();
  const sequence: BoardSequence | null = useSyncExternalStore(
    subscribeToStorage,
    boardSequenceSnapshot,
    () => null,
  );
  const index = sequence?.ids.indexOf(projectId) ?? -1;
  const ids = sequence?.ids ?? [];
  const previousId = adjacentId(ids, index, -1);
  const nextId = adjacentId(ids, index, 1);
  useSequenceShortcuts(previousId, nextId);
  if (sequence === null || index < 0) return null;
  const open = (id: string | null): void => {
    if (id !== null) router.push(DASHBOARD_ROUTES.CREATE_WORKSPACE(id));
  };
  return (
    <div
      className="flex items-center gap-2"
      role="group"
      aria-label={t("label")}
    >
      <NeonButton
        size="sm"
        variant="secondary"
        aria-keyshortcuts={PREVIOUS_KEY}
        disabled={previousId === null}
        onClick={() => open(previousId)}
      >
        {t("previous")}
      </NeonButton>
      <span className="text-xs whitespace-nowrap" style={{ color: TEXT_MUTED }}>
        {t("position", {
          position: index + 1,
          total: ids.length,
          column: sequence.column,
        })}
      </span>
      <NeonButton
        size="sm"
        variant="secondary"
        aria-keyshortcuts={NEXT_KEY}
        disabled={nextId === null}
        onClick={() => open(nextId)}
      >
        {t("next")}
      </NeonButton>
    </div>
  );
}
