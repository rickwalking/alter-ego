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
import { useIsClient } from "@/lib/use-is-client";
import {
  useDocuments,
  useCreateDocument,
  useDeleteDocument,
} from "../hooks/use-documents";
import { useDocumentRetries } from "../hooks/use-document-retries";
import { useDocumentScopeChange } from "../hooks/use-document-scope-change";
import { DocumentList } from "./document-list";
import { DocumentListSkeleton } from "./document-list-skeleton";
import { DocumentForm } from "./document-form";
import { FileUpload } from "./file-upload";
import { type Document, type CreateDocumentRequest } from "@/schemas/knowledge";
import { type DocumentListSectionProps } from "./types";

type ViewMode = "list" | "create" | "upload";

/** Document metadata is free-form JSON: keep only string tags. */
function stringList(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];
}

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
  onRetryDocument,
  retryingIds,
  retryFailedIds,
  onChangeScope,
  changingScopeIds,
  scopeChangeFailedIds,
}: Readonly<DocumentListSectionProps>) {
  const { data: documents } = useDocuments();

  const adaptedDocuments: Document[] = documents.map((doc) => {
    const meta = doc.metadata as Record<string, unknown> | undefined;
    return {
      ...doc,
      tags: stringList(meta?.tags),
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
      onRetryDocument={onRetryDocument}
      retryingIds={retryingIds}
      retryFailedIds={retryFailedIds}
      onChangeScope={onChangeScope}
      changingScopeIds={changingScopeIds}
      scopeChangeFailedIds={scopeChangeFailedIds}
    />
  );
}

export function KnowledgeBaseInterface() {
  const t = useTranslations("knowledge");
  const [viewMode, setViewMode] = useState<ViewMode>("list");
  const createDocument = useCreateDocument();
  const deleteDocument = useDeleteDocument();
  const isClient = useIsClient();
  const { retry, retryingIds, retryFailedIds } = useDocumentRetries();
  const { changeScope, changingScopeIds, scopeChangeFailedIds } =
    useDocumentScopeChange();

  const handleCreateNew = useCallback(() => {
    setViewMode("create");
  }, []);

  const handleUploadNew = useCallback(() => {
    setViewMode("upload");
  }, []);

  const handleSubmit = useCallback(
    (data: CreateDocumentRequest) => {
      createDocument.mutate(data, {
        onSuccess: (created) => {
          setViewMode("list");
          retry(created.id);
        },
      });
    },
    [createDocument, retry],
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

  const renderView = (): React.ReactElement => {
    if (viewMode === "list" && !isClient) {
      return <DocumentListSkeleton />;
    }
    if (viewMode === "list") {
      return (
        <Suspense fallback={<DocumentListSkeleton />}>
          <DocumentListSection
            onCreateNew={handleCreateNew}
            onUploadNew={handleUploadNew}
            onDeleteDocument={handleDelete}
            onRetryDocument={retry}
            retryingIds={retryingIds}
            retryFailedIds={retryFailedIds}
            onChangeScope={changeScope}
            changingScopeIds={changingScopeIds}
            scopeChangeFailedIds={scopeChangeFailedIds}
          />
        </Suspense>
      );
    }
    if (viewMode === "create") {
      return (
        <NeonCard>
          <NeonCardHeader>
            <NeonCardTitle>{t("form.createTitle")}</NeonCardTitle>
          </NeonCardHeader>
          <NeonCardContent>
            <DocumentForm onSubmit={handleSubmit} onCancel={handleCancel} />
          </NeonCardContent>
        </NeonCard>
      );
    }
    return (
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
    );
  };

  return (
    <Container className="py-8">
      <p className="mb-8 text-[var(--color-muted-foreground)]">
        {t("description")}
      </p>

      {renderView()}
    </Container>
  );
}
