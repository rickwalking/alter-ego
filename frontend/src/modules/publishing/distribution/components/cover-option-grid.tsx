"use client";

import Image from "next/image";
import { useTranslations } from "next-intl";
import { API_ENDPOINTS } from "@/constants/api";
import { BG_CARD, NEON_CYAN, TEXT_DIM } from "@/constants/neon";
import type { CoverOptionGridProps, CoverThumbProps } from "./types";

const COVER_SOURCE_OFFER = "offer";
const THUMB_WIDTH = 72;
const THUMB_HEIGHT = 90;
const IDLE_BORDER = "1px solid rgba(255,255,255,0.08)";

/**
 * The slide-1 cover options as a radio group of thumbnails. Each
 * thumbnail is a native button (Tab to reach it, Enter/Space to choose it);
 * the current cover is checked and labelled.
 */
export function CoverOptionGrid({
  options,
  currentAssetId,
  disabled,
  onChoose,
}: Readonly<CoverOptionGridProps>): React.ReactElement {
  const t = useTranslations("publish.coverPicker");
  return (
    <div
      role="radiogroup"
      aria-label={t("title")}
      className="flex flex-wrap gap-3"
    >
      {options.map((option, index) => (
        <CoverThumb
          key={option.asset_id}
          option={option}
          number={index + 1}
          current={option.asset_id === currentAssetId}
          disabled={disabled}
          onChoose={onChoose}
        />
      ))}
    </div>
  );
}

function CoverThumb({
  option,
  number,
  current,
  disabled,
  onChoose,
}: Readonly<CoverThumbProps>): React.ReactElement {
  const t = useTranslations("publish.coverPicker");
  const offer = option.source === COVER_SOURCE_OFFER;
  const label = offer ? t("offerLabel") : t("photoLabel", { number });
  const tag = offer ? t("offerShort") : "";
  const caption = current ? t("current") : tag;
  return (
    <div className="flex flex-col items-center gap-1">
      <button
        type="button"
        role="radio"
        aria-checked={current}
        aria-label={current ? `${label} (${t("current")})` : label}
        disabled={disabled}
        onClick={() => onChoose(option.asset_id)}
        className="focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
        style={{
          width: `${THUMB_WIDTH}px`,
          height: `${THUMB_HEIGHT}px`,
          borderRadius: "6px",
          background: BG_CARD,
          border: current ? `2px solid ${NEON_CYAN}` : IDLE_BORDER,
          padding: 0,
          overflow: "hidden",
          cursor: disabled ? "wait" : "pointer",
        }}
      >
        <Image
          src={API_ENDPOINTS.CREATOR_ASSET_IMAGE(option.asset_id)}
          alt=""
          width={THUMB_WIDTH}
          height={THUMB_HEIGHT}
          className="h-full w-full object-cover"
          unoptimized
        />
      </button>
      <span
        aria-hidden="true"
        className="min-h-4 text-[11px]"
        style={{ color: current ? NEON_CYAN : TEXT_DIM }}
      >
        {caption}
      </span>
    </div>
  );
}
