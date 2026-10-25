"use client";

import { useTranslations } from "next-intl";
import { TEXT_DIM } from "@/constants/neon";
import type { CoverPhotoUploadFieldProps } from "./types";

const ACCEPTED_PHOTO_TYPES = "image/png,image/webp,image/jpeg";

/**
 * "Enviar foto": picks a file from the device for the owner's library. The
 * refusal sentence is the wizard's upload error (same endpoint and limits).
 */
export function CoverPhotoUploadField({
  upload,
  disabled,
}: Readonly<CoverPhotoUploadFieldProps>): React.ReactElement | null {
  const t = useTranslations("publish.coverPicker.generate");
  if (!upload.available) {
    return null;
  }
  return (
    <div className="mb-3">
      <label className="block text-xs" style={{ color: TEXT_DIM }}>
        {upload.uploading ? t("uploading") : t("upload")}
        <input
          type="file"
          accept={ACCEPTED_PHOTO_TYPES}
          disabled={disabled || upload.uploading}
          onChange={(e) => {
            const file = e.target.files?.[0];
            e.target.value = "";
            if (file) {
              void upload.onFile(file);
            }
          }}
          className="mt-1 block text-xs"
        />
      </label>
      {upload.failed && (
        <p role="alert" className="mt-1 text-xs text-red-400">
          {t("uploadFailed")}
        </p>
      )}
    </div>
  );
}
