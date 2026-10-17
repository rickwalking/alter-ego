"use client";

import Image from "next/image";
import { useTranslations } from "next-intl";
import { API_ENDPOINTS } from "@/constants/api";
import { BG_CARD, NEON_AMBER, NEON_CYAN, TEXT_MUTED } from "@/constants/neon";
import { sectionCardStyle, sectionHeaderStyle } from "./section-styles";

export interface PhotoOption {
  id: string;
  pose_tag?: string | null;
}

export interface CreatePhotoSectionProps {
  photos: readonly PhotoOption[];
  selectedId: string;
  onSelect: (id: string) => void;
  onUpload: (file: File) => void;
  uploading: boolean;
  uploadFailed: boolean;
}

const ACCEPTED_PHOTO_TYPES = "image/png,image/webp,image/jpeg";

/**
 * AE-0376: "Foto do slide 1" for Ponto de Vista decks. Pick a cut-out photo
 * from the library (newest first, the default) or upload a new one.
 */
export function CreatePhotoSection({
  photos,
  selectedId,
  onSelect,
  onUpload,
  uploading,
  uploadFailed,
}: CreatePhotoSectionProps): React.ReactElement {
  const t = useTranslations("create.photo");
  return (
    <div style={sectionCardStyle}>
      <div style={sectionHeaderStyle}>{t("title")}</div>
      <p style={{ fontSize: "11px", color: TEXT_MUTED, marginBottom: "10px" }}>
        {t("hint")}
      </p>
      {photos.length === 0 ? (
        <p role="note" style={{ fontSize: "12px", color: NEON_AMBER }}>
          {t("empty")}
        </p>
      ) : (
        <div
          role="radiogroup"
          aria-label={t("title")}
          className="flex flex-wrap gap-2.5"
        >
          {photos.map((photo) => (
            <button
              key={photo.id}
              type="button"
              role="radio"
              aria-checked={photo.id === selectedId}
              aria-label={photo.pose_tag || t("photoLabel")}
              onClick={() => onSelect(photo.id)}
              style={{
                width: "72px",
                height: "90px",
                borderRadius: "6px",
                background: BG_CARD,
                border:
                  photo.id === selectedId
                    ? `2px solid ${NEON_CYAN}`
                    : "1px solid rgba(255,255,255,0.08)",
                padding: 0,
                overflow: "hidden",
                cursor: "pointer",
              }}
            >
              <Image
                src={API_ENDPOINTS.CREATOR_ASSET_IMAGE(photo.id)}
                alt={photo.pose_tag || t("photoLabel")}
                width={72}
                height={90}
                className="h-full w-full object-contain"
                unoptimized
              />
            </button>
          ))}
        </div>
      )}
      <label
        style={{
          display: "block",
          marginTop: "12px",
          fontSize: "12px",
          color: TEXT_MUTED,
        }}
      >
        {uploading ? t("uploading") : t("upload")}
        <input
          type="file"
          accept={ACCEPTED_PHOTO_TYPES}
          disabled={uploading}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) {
              onUpload(file);
            }
          }}
          style={{ display: "block", marginTop: "6px" }}
        />
      </label>
      {uploadFailed && (
        <p role="alert" className="text-red-400" style={{ fontSize: "12px" }}>
          {t("uploadFailed")}
        </p>
      )}
    </div>
  );
}
