"use client";
import { NeonButton } from "@/components/atoms/neon-button";

import { useTranslations } from "next-intl";
import { useFileUploadForm } from "../hooks/use-file-upload-form";
import { isAllowedUploadFile } from "./file-upload-checks";
import { UploadDropZone } from "./file-upload-drop-zone";
import {
  UploadErrorNotice,
  UploadMetadataFields,
  UploadProgressBar,
  UploadSuccess,
} from "./file-upload-parts";
import { type FileUploadProps } from "./types";

export function FileUpload({
  onUploadComplete,
  onCancel,
}: Readonly<FileUploadProps>) {
  const t = useTranslations("knowledge.upload");
  const form = useFileUploadForm();
  const { upload, selectedFile } = form;
  const isFileTypeValid = isAllowedUploadFile(selectedFile);

  if (upload.isSuccess) {
    return <UploadSuccess onDone={onUploadComplete} />;
  }

  return (
    <div className="space-y-6">
      <UploadDropZone form={form} typeValid={isFileTypeValid} />

      {upload.isPending && <UploadProgressBar progress={form.progress} />}
      {upload.isError && <UploadErrorNotice message={upload.error.message} />}
      {selectedFile && (
        <UploadMetadataFields
          title={form.title}
          onTitleChange={form.setTitle}
          tags={form.tags}
          onTagsChange={form.setTags}
          disabled={upload.isPending}
        />
      )}

      {/* Actions */}
      <div className="flex justify-end gap-3">
        {onCancel && (
          <NeonButton
            type="button"
            variant="outline"
            onClick={onCancel}
            disabled={upload.isPending}
          >
            {t("cancel")}
          </NeonButton>
        )}
        <NeonButton
          onClick={() => form.submit(onUploadComplete)}
          disabled={!selectedFile || !isFileTypeValid || upload.isPending}
        >
          {upload.isPending ? t("uploading") : t("uploadButton")}
        </NeonButton>
      </div>
    </div>
  );
}
