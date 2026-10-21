"use client";

import { useCallback, useState } from "react";
import { useTranslations } from "next-intl";
import { TEXT_DIM } from "@/constants/neon";
import { HTTP_STATUS } from "@/constants/api";
import { ApiError } from "@/lib/api-client";
import { SECTION_CARD_STYLE } from "@/modules/publishing/distribution/constants";
import {
  useCoverOptions,
  usePickCover,
} from "@/modules/publishing/distribution/hooks/use-cover-picker";
import { CoverOptionGrid } from "./cover-option-grid";
import type {
  CoverPick,
  CoverPickDeps,
  CoverPickerSectionProps,
  PickStatusProps,
} from "./types";

function failureKey(error: Error | null): "conflict" | "failed" {
  if (error instanceof ApiError && error.status === HTTP_STATUS.CONFLICT) {
    return "conflict";
  }
  return "failed";
}

/** Swap slide 1 to a chosen asset (ignored while busy or for the current one). */
function useCoverPick({
  projectId,
  currentAssetId,
  onSwitched,
}: CoverPickDeps): CoverPick {
  const pick = usePickCover();
  const [switched, setSwitched] = useState(false);
  const handleChoose = useCallback(
    (assetId: string): void => {
      if (pick.isPending || assetId === currentAssetId) {
        return;
      }
      setSwitched(false);
      pick.mutate(
        { projectId, assetId },
        {
          onSuccess: (data) => {
            setSwitched(true);
            onSwitched(data.artifact_version ?? null);
          },
        },
      );
    },
    [pick, currentAssetId, projectId, onSwitched],
  );
  return { pick, switched, handleChoose };
}

/** "Switching…" while the swap runs, then the success line. */
function PickStatus({
  pending,
  switched,
  switchingText,
  successText,
}: Readonly<PickStatusProps>): React.ReactElement | null {
  if (pending) {
    return <span role="status">{switchingText}</span>;
  }
  if (!switched) {
    return null;
  }
  return (
    <span role="status" className="text-success">
      {successText}
    </span>
  );
}

/**
 * "Capa (slide 1)" on the publish step of a Ponto de Vista carousel.
 * Lists the owner's library photos (and the GrokBot offer), marks the current
 * one, and swaps slide 1 on a pick: the server re-renders slides + PDFs, then
 * `onSwitched` refreshes the previews with the new artifact version.
 */
export function CoverPickerSection({
  projectId,
  onSwitched,
}: Readonly<CoverPickerSectionProps>): React.ReactElement {
  const t = useTranslations("publish.coverPicker");
  const options = useCoverOptions(projectId);
  const currentAssetId = options.data?.current_asset_id ?? null;
  const { pick, switched, handleChoose } = useCoverPick({
    projectId,
    currentAssetId,
    onSwitched,
  });

  const items = options.data?.options ?? [];
  return (
    <section style={SECTION_CARD_STYLE} aria-labelledby="cover-picker-title">
      <h3 id="cover-picker-title" className="text-sm font-semibold mb-1">
        {t("title")}
      </h3>
      <p className="text-xs mb-3" style={{ color: TEXT_DIM }}>
        {t("description")}
      </p>
      {options.isError && (
        <p role="alert" className="text-xs text-red-400">
          {t("loadFailed")}
        </p>
      )}
      {options.isSuccess && items.length === 0 && (
        <p role="note" className="text-xs" style={{ color: TEXT_DIM }}>
          {t("empty")}
        </p>
      )}
      {items.length > 0 && (
        <CoverOptionGrid
          options={items}
          currentAssetId={currentAssetId}
          disabled={pick.isPending}
          onChoose={handleChoose}
        />
      )}
      <div className="mt-3 text-xs" aria-live="polite">
        <PickStatus
          pending={pick.isPending}
          switched={switched}
          switchingText={t("switching")}
          successText={t("success")}
        />
      </div>
      {pick.isError && (
        <p role="alert" className="text-xs text-red-400">
          {t(failureKey(pick.error))}
        </p>
      )}
    </section>
  );
}
