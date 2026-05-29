"use client";
import { NeonCard, NeonCardContent, NeonCardHeader, NeonCardTitle } from "@/components/molecules/neon-card";

import { useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { Container } from "@/components/layout";
import {
  useDocuments,
  useCreateDocument,
  useDeleteDocument,
} from "../hooks/use-documents";
import { DocumentList } from "./document-list";
import { DocumentForm } from "./document-form";
import { FileUpload } from "./file-upload";
import { type Document, type CreateDocumentRequest } from "@/schemas/knowledge";

type ViewMode = "list" | "create" | "upload";

export function KnowledgeBaseInterface() {
  const t = useTranslations("knowledge");
  const [viewMode, setViewMode] = useState<ViewMode>("list");
  const { data: documents = [], isLoading } = useDocuments();
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
    <Container className="py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">{t("title")}</h1>
        <p className="text-[var(--color-muted-foreground)] mt-2">
          {t("description")}
        </p>
      </div>

      {viewMode === "list" ? (
        <DocumentList
          documents={adaptedDocuments}
          isLoading={isLoading}
          onCreateNew={handleCreateNew}
          onUploadNew={handleUploadNew}
          onDeleteDocument={handleDelete}
        />
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
