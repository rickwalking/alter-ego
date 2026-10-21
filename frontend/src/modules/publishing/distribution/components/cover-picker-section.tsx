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
import type { CoverPickerSectionProps } from "./types";

function failureKey(error: Error | null): "conflict" | "failed" {
  if (error instanceof ApiError && error.status === HTTP_STATUS.CONFLICT) {
    return "conflict";
  }
  return "failed";
}

/**
 * AE-0445: "Capa (slide 1)" on the publish step of a Ponto de Vista carousel.
 * Lists the owner's library photos (and the GrokBot offer), marks the current
 * one, and swaps slide 1 on a pick: the server re-renders slides + PDFs, then
 * `onSwitched` refreshes the previews with the new artifact version.
 */
export function CoverPickerSection({
  projectId,
  lockVersion,
  onSwitched,
}: CoverPickerSectionProps): React.ReactElement {
  const t = useTranslations("publish.coverPicker");
  const options = useCoverOptions(projectId);
  const pick = usePickCover();
  const [switched, setSwitched] = useState(false);

  const handleChoose = useCallback(
    (assetId: string): void => {
      if (pick.isPending || assetId === options.data?.current_asset_id) {
        return;
      }
      setSwitched(false);
      pick.mutate(
        { projectId, assetId, expectedVersion: lockVersion },
        {
          onSuccess: (data) => {
            setSwitched(true);
            onSwitched(data.artifact_version ?? null);
          },
        },
      );
    },
    [pick, options.data?.current_asset_id, projectId, lockVersion, onSwitched],
  );

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
          currentAssetId={options.data?.current_asset_id ?? null}
          disabled={pick.isPending}
          onChoose={handleChoose}
        />
      )}
      <div className="mt-3 text-xs" aria-live="polite">
        {pick.isPending && <span role="status">{t("switching")}</span>}
        {switched && !pick.isPending && (
          <span role="status" className="text-success">
            {t("success")}
          </span>
        )}
      </div>
      {pick.isError && (
        <p role="alert" className="text-xs text-red-400">
          {t(failureKey(pick.error))}
        </p>
      )}
    </section>
  );
}
