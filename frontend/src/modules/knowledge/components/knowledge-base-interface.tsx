"use client";
import {
  NeonCard,
  NeonCardContent,
  NeonCardHeader,
  NeonCardTitle,
} from "@/components/molecules/neon-card";

import { Suspense, useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { Container } from "@/components/layout";
import {
  useDocuments,
  useCreateDocument,
  useDeleteDocument,
} from "../hooks/use-documents";
import { DocumentList } from "./document-list";
import { DocumentListSkeleton } from "./document-list-skeleton";
import { DocumentForm } from "./document-form";
import { FileUpload } from "./file-upload";
import { type Document, type CreateDocumentRequest } from "@/schemas/knowledge";
import { type DocumentListSectionProps } from "./types";

type ViewMode = "list" | "create" | "upload";

/**
 * Data-bound list subtree (ADR-010). Reads documents via the Suspense query
 * (`useDocuments`); the parent's `<Suspense>` renders the skeleton while it
 * loads and the route-level `error.tsx` boundary handles fetch errors. No
 * `isLoading` branch lives here.
 */
function DocumentListSection({
  onCreateNew,
  onUploadNew,
  onDeleteDocument,
}: DocumentListSectionProps) {
  const { data: documents } = useDocuments();

  const adaptedDocuments: Document[] = documents.map((doc) => {
    const meta = doc.metadata as Record<string, unknown> | undefined;
    return {
      ...doc,
      tags: (meta?.tags as string[]) ?? [],
      createdAt: doc.created_at,
      updatedAt: doc.updated_at,
    };
  });

  return (
    <DocumentList
      documents={adaptedDocuments}
      onCreateNew={onCreateNew}
      onUploadNew={onUploadNew}
      onDeleteDocument={onDeleteDocument}
    />
  );
}

export function KnowledgeBaseInterface() {
  const t = useTranslations("knowledge");
  const [viewMode, setViewMode] = useState<ViewMode>("list");
  const createDocument = useCreateDocument();
  const deleteDocument = useDeleteDocument();

  const handleCreateNew = useCallback(() => {
    setViewMode("create");
  }, []);

  const handleUploadNew = useCallback(() => {
    setViewMode("upload");
  }, []);

  const handleSubmit = useCallback(
    (data: CreateDocumentRequest) => {
      createDocument.mutate(data, {
        onSuccess: () => {
          setViewMode("list");
        },
      });
    },
    [createDocument],
  );

  const handleUploadComplete = useCallback(() => {
    setViewMode("list");
  }, []);

  const handleCancel = useCallback(() => {
    setViewMode("list");
  }, []);

  const handleDelete = useCallback(
    (id: string) => {
      deleteDocument.mutate(id);
    },
    [deleteDocument],
  );

  return (
    <Container className="py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">{t("title")}</h1>
        <p className="text-[var(--color-muted-foreground)] mt-2">
          {t("description")}
        </p>
      </div>

      {viewMode === "list" ? (
        <Suspense fallback={<DocumentListSkeleton />}>
          <DocumentListSection
            onCreateNew={handleCreateNew}
            onUploadNew={handleUploadNew}
            onDeleteDocument={handleDelete}
          />
        </Suspense>
      ) : viewMode === "create" ? (
        <NeonCard>
          <NeonCardHeader>
            <NeonCardTitle>{t("form.createTitle")}</NeonCardTitle>
          </NeonCardHeader>
          <NeonCardContent>
            <DocumentForm onSubmit={handleSubmit} onCancel={handleCancel} />
          </NeonCardContent>
        </NeonCard>
      ) : (
        <NeonCard>
          <NeonCardHeader>
            <NeonCardTitle>{t("upload.title")}</NeonCardTitle>
          </NeonCardHeader>
          <NeonCardContent>
            <FileUpload
              onUploadComplete={handleUploadComplete}
              onCancel={handleCancel}
            />
          </NeonCardContent>
        </NeonCard>
      )}
    </Container>
  );
}
