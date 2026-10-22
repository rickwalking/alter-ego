import { useMutation, useQueryClient } from "@tanstack/react-query";
import { HTTP_STATUS } from "@/constants/api";
import { DOCUMENT_SCOPE } from "@/constants/knowledge";
import { ApiError } from "@/lib/api-client";
import {
  documentUploadResponseSchema,
  type DocumentUploadResponse,
  type Document,
} from "@/schemas/knowledge";
import { documentKeys } from "@/modules/knowledge/queries";
import type { UploadDocumentInput } from "./types";

/** The multipart body of an upload: the file, its fields and its scope. */
export function uploadFormData({
  file,
  title,
  tags,
  scope = DOCUMENT_SCOPE.PERSONAL,
}: UploadDocumentInput): FormData {
  const formData = new FormData();
  formData.append("file", file);
  if (title) formData.append("title", title);
  if (tags) formData.append("tags", tags);
  formData.append("scope", scope);
  formData.append("is_public", String(scope === DOCUMENT_SCOPE.PUBLIC));
  return formData;
}

/** A 2xx body that matches the schema, else the matching ApiError. */
function parseUploadResponse(xhr: XMLHttpRequest): DocumentUploadResponse {
  const isSuccess =
    xhr.status >= HTTP_STATUS.OK && xhr.status < HTTP_STATUS.MULTIPLE_CHOICES;
  if (!isSuccess) {
    throw new ApiError(xhr.status, xhr.statusText);
  }
  let json: unknown;
  try {
    json = JSON.parse(xhr.responseText);
  } catch {
    throw new ApiError(xhr.status, "Failed to parse response");
  }
  const result = documentUploadResponseSchema.safeParse(json);
  if (!result.success) {
    throw new ApiError(xhr.status, "Invalid response format");
  }
  return result.data;
}

/** POST the file with an XHR so upload progress can be reported. */
function uploadWithProgress(
  input: UploadDocumentInput,
): Promise<DocumentUploadResponse> {
  const xhr = new XMLHttpRequest();
  return new Promise<DocumentUploadResponse>((resolve, reject) => {
    xhr.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable && input.onProgress) {
        input.onProgress(Math.round((event.loaded / event.total) * 100));
      }
    });
    xhr.addEventListener("load", () => {
      try {
        resolve(parseUploadResponse(xhr));
      } catch (error) {
        reject(error instanceof Error ? error : new Error(String(error)));
      }
    });
    xhr.addEventListener("error", () => {
      reject(new ApiError(0, "Network error"));
    });
    xhr.open("POST", "/api/documents/upload");
    xhr.send(uploadFormData(input));
  });
}

/** Put the new document first in the cached list (once). */
function prependDocument(
  document: DocumentUploadResponse,
): (previous: Document[] | undefined) => Document[] | undefined {
  return (previous) =>
    previous
      ? [document, ...previous.filter((item) => item.id !== document.id)]
      : previous;
}

export function useUploadDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: uploadWithProgress,
    onSuccess: (document) => {
      queryClient.setQueryData(documentKeys.detail(document.id), document);
      queryClient.setQueryData<Document[]>(
        documentKeys.list(),
        prependDocument(document),
      );
      void queryClient.invalidateQueries({ queryKey: documentKeys.list() });
    },
  });
}
