"use client";

import { useTranslations } from "next-intl";
import { CREATOR_PHOTO_ACCEPTED_TYPES } from "@/constants/create";
import { TEXT_DIM } from "@/constants/neon";
import { UPLOAD_FAILURE } from "@/modules/publishing/distribution/constants";
import type { CoverPhotoUploadFieldProps } from "./types";

/**
 * "Enviar foto": picks a file from the device for the owner's library. A
 * refused file shows the wizard's upload sentence (same endpoint and limits);
 * a rate limit, a network or a server failure says so instead.
 */
export function CoverPhotoUploadField({
  upload,
  disabled,
}: Readonly<CoverPhotoUploadFieldProps>): React.ReactElement | null {
  const t = useTranslations("publish.coverPicker.generate");
  const tPhoto = useTranslations("create.photo");
  if (!upload.available) {
    return null;
  }
  return (
    <div className="mb-3">
      <label className="block text-xs" style={{ color: TEXT_DIM }}>
        {upload.uploading ? t("uploading") : t("upload")}
        <input
          type="file"
          accept={CREATOR_PHOTO_ACCEPTED_TYPES}
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
      {upload.failure && (
        <p role="alert" className="mt-1 text-xs text-red-400">
          {upload.failure === UPLOAD_FAILURE.INVALID
            ? tPhoto("uploadFailed")
            : t(`uploadErrors.${upload.failure}`)}
        </p>
      )}
    </div>
  );
}
