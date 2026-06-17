import { useMutation, useQueryClient } from "@tanstack/react-query";
import { HTTP_STATUS } from "@/constants/api";
import { ApiError } from "@/lib/api-client";
import {
  documentUploadResponseSchema,
  type DocumentUploadResponse,
  type Document,
} from "@/schemas/knowledge";
import { documentKeys } from "@/modules/knowledge/queries";

export function useUploadDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      file,
      title,
      tags,
      onProgress,
    }: {
      file: File;
      title?: string;
      tags?: string;
      onProgress?: (progress: number) => void;
    }) => {
      const formData = new FormData();
      formData.append("file", file);
      if (title) formData.append("title", title);
      if (tags) formData.append("tags", tags);

      const xhr = new XMLHttpRequest();
      const promise = new Promise<DocumentUploadResponse>((resolve, reject) => {
        xhr.upload.addEventListener("progress", (event) => {
          if (event.lengthComputable && onProgress) {
            onProgress(Math.round((event.loaded / event.total) * 100));
          }
        });

        xhr.addEventListener("load", () => {
          if (
            xhr.status >= HTTP_STATUS.OK &&
            xhr.status < HTTP_STATUS.MULTIPLE_CHOICES
          ) {
            try {
              const json = JSON.parse(xhr.responseText);
              const result = documentUploadResponseSchema.safeParse(json);
              if (result.success) {
                resolve(result.data);
              } else {
                reject(new ApiError(xhr.status, "Invalid response format"));
              }
            } catch {
              reject(new ApiError(xhr.status, "Failed to parse response"));
            }
          } else {
            reject(new ApiError(xhr.status, xhr.statusText));
          }
        });

        xhr.addEventListener("error", () => {
          reject(new ApiError(0, "Network error"));
        });

        xhr.open("POST", "/api/documents/upload");
        xhr.send(formData);
      });

      return promise;
    },
    onSuccess: (document) => {
      queryClient.setQueryData(documentKeys.detail(document.id), document);
      queryClient.setQueryData<Document[]>(documentKeys.list(), (previous) =>
        previous
          ? [document, ...previous.filter((item) => item.id !== document.id)]
          : previous,
      );
      void queryClient.invalidateQueries({ queryKey: documentKeys.list() });
    },
  });
}
