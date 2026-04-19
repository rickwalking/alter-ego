"use client";

import { useState, useCallback, useRef } from "react";
import { useTranslations } from "next-intl";
import { Upload, X, FileText, CheckCircle, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { useUploadDocument } from "../hooks/use-upload";

interface FileUploadProps {
  onUploadComplete?: () => void;
  onCancel?: () => void;
}

export function FileUpload({ onUploadComplete, onCancel }: FileUploadProps) {
  const t = useTranslations("knowledge.upload");
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [tags, setTags] = useState("");
  const [progress, setProgress] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const upload = useUploadDocument();

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      setSelectedFile(files[0]);
      if (!title) setTitle(files[0].name.replace(/\.[^/.]+$/, ""));
    }
  }, [title]);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      setSelectedFile(files[0]);
      if (!title) setTitle(files[0].name.replace(/\.[^/.]+$/, ""));
    }
  }, [title]);

  const handleUpload = useCallback(() => {
    if (!selectedFile) return;

    setProgress(0);
    upload.mutate(
      {
        file: selectedFile,
        title: title || selectedFile.name,
        tags,
        onProgress: setProgress,
      },
      {
        onSuccess: () => {
          setSelectedFile(null);
          setTitle("");
          setTags("");
          setProgress(0);
          onUploadComplete?.();
        },
      }
    );
  }, [selectedFile, title, tags, upload, onUploadComplete]);

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const allowedTypes = [
    "application/pdf",
    "text/plain",
    "text/markdown",
    "text/x-markdown",
  ];

  const isFileTypeValid = selectedFile
    ? allowedTypes.includes(selectedFile.type) ||
      /\.(pdf|txt|md|markdown)$/i.test(selectedFile.name)
    : true;

  if (upload.isSuccess) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <CheckCircle className="h-12 w-12 text-green-500 mb-4" />
        <h3 className="text-lg font-semibold">{t("success.title")}</h3>
        <p className="text-sm text-[var(--color-muted-foreground)] mt-1">
          {t("success.description")}
        </p>
        <Button className="mt-4" onClick={onUploadComplete}>
          {t("success.done")}
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Drop Zone */}
      <div
        className={cn(
          "relative rounded-lg border-2 border-dashed p-8 text-center transition-colors",
          isDragging
            ? "border-[var(--color-primary)] bg-[var(--color-primary)]/5"
            : "border-[var(--color-border)] hover:border-[var(--color-primary)]/50",
          upload.isPending && "pointer-events-none opacity-50"
        )}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        role="region"
        aria-label="File upload area"
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.txt,.md,.markdown"
          className="hidden"
          onChange={handleFileSelect}
          disabled={upload.isPending}
          aria-label="Select file to upload"
        />

        {selectedFile ? (
          <div className="space-y-3">
            <div className="flex items-center justify-center gap-3">
              <FileText className="h-8 w-8 text-[var(--color-primary)]" aria-hidden="true" />
              <div className="text-left">
                <p className="font-medium">{selectedFile.name}</p>
                <p className="text-sm text-[var(--color-muted-foreground)]">
                  {formatFileSize(selectedFile.size)}
                </p>
              </div>
              {!upload.isPending && (
                <button
                  type="button"
                  onClick={() => {
                    setSelectedFile(null);
                    setTitle("");
                  }}
                  className="ml-2 rounded-full p-1 hover:bg-[var(--color-muted)]"
                  aria-label="Remove selected file"
                >
                  <X className="h-4 w-4" aria-hidden="true" />
                </button>
              )}
            </div>
            {!isFileTypeValid && (
              <div className="flex items-center justify-center gap-2 text-sm text-[var(--color-destructive)]" role="alert">
                <AlertCircle className="h-4 w-4" aria-hidden="true" />
                {t("error.fileType")}
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            <Upload className="mx-auto h-10 w-10 text-[var(--color-muted-foreground)]" aria-hidden="true" />
            <div>
              <p className="font-medium">
                {t("dropText")}{" "}
                <button
                  type="button"
                  className="text-[var(--color-primary)] hover:underline"
                  onClick={() => fileInputRef.current?.click()}
                >
                  {t("browse")}
                </button>
              </p>
              <p className="text-sm text-[var(--color-muted-foreground)] mt-1">
                {t("supports")}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Upload Progress */}
      {upload.isPending && (
        <div className="space-y-2" role="status" aria-label="Upload progress">
          <div className="flex items-center justify-between text-sm">
            <span className="text-[var(--color-muted-foreground)]">
              {t("uploading")}
            </span>
            <span className="font-medium" aria-live="polite">{progress}%</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-[var(--color-muted)]" role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100}>
            <div
              className="h-full bg-[var(--color-primary)] transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Error */}
      {upload.isError && (
        <div className="flex items-center gap-2 rounded-lg border border-[var(--color-destructive)]/20 bg-[var(--color-destructive)]/5 p-3 text-sm text-[var(--color-destructive)]" role="alert">
          <AlertCircle className="h-4 w-4 shrink-0" aria-hidden="true" />
          {upload.error?.message || t("error.generic")}
        </div>
      )}

      {/* Metadata Fields */}
      {selectedFile && (
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="upload-title">{t("fields.title")}</Label>
            <Input
              id="upload-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={t("fields.titlePlaceholder")}
              disabled={upload.isPending}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="upload-tags">{t("fields.tags")}</Label>
            <Input
              id="upload-tags"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder={t("fields.tagsPlaceholder")}
              disabled={upload.isPending}
            />
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex justify-end gap-3">
        {onCancel && (
          <Button
            type="button"
            variant="outline"
            onClick={onCancel}
            disabled={upload.isPending}
          >
            {t("cancel")}
          </Button>
        )}
        <Button
          onClick={handleUpload}
          disabled={!selectedFile || !isFileTypeValid || upload.isPending}
        >
          {upload.isPending ? t("uploading") : t("uploadButton")}
        </Button>
      </div>
    </div>
  );
}
