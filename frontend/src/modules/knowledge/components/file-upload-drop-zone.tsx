"use client";

import { useRef } from "react";
import { useTranslations } from "next-intl";
import { AlertCircle, FileText, Upload, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatFileSize } from "./file-upload-checks";
import type { DropZoneProps, SelectedFileSummaryProps } from "./types";

export function SelectedFileSummary({
  file,
  pending,
  typeValid,
  onRemove,
}: Readonly<SelectedFileSummaryProps>): React.ReactElement {
  const t = useTranslations("knowledge.upload");
  const tDocument = useTranslations("knowledge.document");
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-center gap-3">
        <FileText
          className="h-8 w-8 text-[var(--color-primary)]"
          aria-hidden="true"
        />
        <div className="text-left">
          <p className="font-medium">{file.name}</p>
          <p className="text-sm text-[var(--color-muted-foreground)]">
            {formatFileSize(file.size)}
          </p>
        </div>
        {!pending && (
          <button
            type="button"
            onClick={onRemove}
            className="ml-2 rounded-full p-1 hover:bg-[var(--color-muted)]"
            aria-label={tDocument("removeFile")}
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        )}
      </div>
      {!typeValid && (
        <div
          className="flex items-center justify-center gap-2 text-sm text-[var(--color-destructive)]"
          role="alert"
        >
          <AlertCircle className="h-4 w-4" aria-hidden="true" />
          {t("error.fileType")}
        </div>
      )}
    </div>
  );
}

export function EmptyDropPrompt({
  onBrowse,
}: Readonly<{
  onBrowse: () => void;
}>): React.ReactElement {
  const t = useTranslations("knowledge.upload");
  return (
    <div className="space-y-3">
      <Upload
        className="mx-auto h-10 w-10 text-[var(--color-muted-foreground)]"
        aria-hidden="true"
      />
      <div>
        <p className="font-medium">
          {t("dropText")}{" "}
          <button
            type="button"
            className="text-[var(--color-primary)] hover:underline"
            onClick={onBrowse}
          >
            {t("browse")}
          </button>
        </p>
        <p className="text-sm text-[var(--color-muted-foreground)] mt-1">
          {t("supports")}
        </p>
      </div>
    </div>
  );
}

export function UploadDropZone({
  form,
  typeValid,
}: Readonly<DropZoneProps>): React.ReactElement {
  const t = useTranslations("knowledge.upload");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { upload, selectedFile } = form;
  return (
    <div
      className={cn(
        "relative rounded-lg border-2 border-dashed p-8 text-center transition-colors",
        form.isDragging
          ? "border-[var(--color-primary)] bg-[var(--color-primary)]/5"
          : "border-[var(--color-border)] hover:border-[var(--color-primary)]/50",
        upload.isPending && "pointer-events-none opacity-50",
      )}
      {...form.dropZone}
      role="region"
      aria-label={t("dropZone")}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.txt,.md,.markdown"
        className="hidden"
        onChange={form.onFileInput}
        disabled={upload.isPending}
        aria-label={t("selectFile")}
      />
      {selectedFile ? (
        <SelectedFileSummary
          file={selectedFile}
          pending={upload.isPending}
          typeValid={typeValid}
          onRemove={form.clearFile}
        />
      ) : (
        <EmptyDropPrompt onBrowse={() => fileInputRef.current?.click()} />
      )}
    </div>
  );
}
