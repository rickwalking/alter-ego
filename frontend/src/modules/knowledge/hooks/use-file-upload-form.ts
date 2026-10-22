"use client";

import { useCallback, useState } from "react";
import { useUploadDocument } from "./use-upload";
import {
  DOCUMENT_SCOPE,
  type DocumentScopeChoice,
} from "@/constants/knowledge";
import type { FilePick, FileUploadForm, UploadFields } from "./types";

const FILE_EXTENSION = /\.[^/.]+$/;

/** Drag/drop + file picker state; the title defaults to the file name. */
function useFilePick(
  title: string,
  setTitle: (value: string) => void,
): FilePick {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const pick = useCallback(
    (file: File | undefined) => {
      if (!file) return;
      setSelectedFile(file);
      if (!title) setTitle(file.name.replace(FILE_EXTENSION, ""));
    },
    [title, setTitle],
  );
  const dropZone = {
    onDragOver: (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(true);
    },
    onDragLeave: (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
    },
    onDrop: (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      pick(e.dataTransfer.files[0]);
    },
  };
  const onFileInput = (e: React.ChangeEvent<HTMLInputElement>) =>
    pick(e.target.files?.[0]);
  return { isDragging, selectedFile, setSelectedFile, dropZone, onFileInput };
}

/** Title, tags and scope of the upload, with a reset to their defaults. */
function useUploadFields(): UploadFields {
  const [title, setTitle] = useState("");
  const [tags, setTags] = useState("");
  const [scope, setScope] = useState<DocumentScopeChoice>(
    DOCUMENT_SCOPE.PERSONAL,
  );
  const reset = (): void => {
    setTitle("");
    setTags("");
    setScope(DOCUMENT_SCOPE.PERSONAL);
  };
  return { title, setTitle, tags, setTags, scope, setScope, reset };
}

export function useFileUploadForm(): FileUploadForm {
  const { reset, ...fields } = useUploadFields();
  const { title, setTitle, tags, scope } = fields;
  const [progress, setProgress] = useState(0);
  const upload = useUploadDocument();
  const { selectedFile, setSelectedFile, ...pick } = useFilePick(
    title,
    setTitle,
  );

  const submit = (onDone?: () => void): void => {
    if (!selectedFile) return;
    setProgress(0);
    upload.mutate(
      {
        file: selectedFile,
        title: title || selectedFile.name,
        tags,
        scope,
        onProgress: setProgress,
      },
      {
        onSuccess: () => {
          setSelectedFile(null);
          reset();
          setProgress(0);
          onDone?.();
        },
      },
    );
  };
  const clearFile = (): void => {
    setSelectedFile(null);
    setTitle("");
  };
  return {
    ...pick,
    ...fields,
    selectedFile,
    progress,
    clearFile,
    submit,
    upload,
  };
}
