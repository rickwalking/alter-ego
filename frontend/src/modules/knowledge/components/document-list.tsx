"use client";
import { NeonInput } from "@/components/atoms/neon-input";
import { NeonButton } from "@/components/atoms/neon-button";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Search, Plus, Upload } from "lucide-react";
import { SCOPE_FILTER_ALL, type ScopeFilterValue } from "@/constants/knowledge";
import { DocumentCard } from "./document-card";
import { scopeChoiceOf } from "./document-scope";
import { ScopeFilter } from "./scope-parts";
import { type DocumentListProps } from "./types";

const NO_IDS: ReadonlySet<string> = new Set();

export function DocumentList({
  documents,
  onCreateNew,
  onUploadNew,
  onDeleteDocument,
  onRetryDocument,
  retryingIds = NO_IDS,
  retryFailedIds = NO_IDS,
  onChangeScope,
  changingScopeIds = NO_IDS,
  scopeChangeFailedIds = NO_IDS,
}: Readonly<DocumentListProps>) {
  const t = useTranslations("knowledge");
  const [searchQuery, setSearchQuery] = useState("");
  const [scopeFilter, setScopeFilter] =
    useState<ScopeFilterValue>(SCOPE_FILTER_ALL);

  const inScope = (doc: DocumentListProps["documents"][number]): boolean =>
    scopeFilter === SCOPE_FILTER_ALL ||
    scopeChoiceOf(doc.scope) === scopeFilter;

  const filteredDocuments = documents.filter(inScope).filter((doc) => {
    const meta = doc.metadata as Record<string, unknown> | undefined;
    const tags = (meta?.tags as string[] | undefined) ?? [];
    return (
      doc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.status.toLowerCase().includes(searchQuery.toLowerCase()) ||
      tags.some((tag) => tag.toLowerCase().includes(searchQuery.toLowerCase()))
    );
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-4">
        <div className="relative min-w-[12rem] flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--color-muted-foreground)]" />
          <NeonInput
            placeholder={t("search")}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
        <ScopeFilter value={scopeFilter} onChange={setScopeFilter} />
        <NeonButton onClick={onUploadNew} variant="outline" className="gap-2">
          <Upload className="h-4 w-4" />
          {t("uploadButton")}
        </NeonButton>
        <NeonButton onClick={onCreateNew} className="gap-2">
          <Plus className="h-4 w-4" />
          {t("newDocument")}
        </NeonButton>
      </div>

      {filteredDocuments.length === 0 ? (
        <div className="text-center py-12 text-[var(--color-muted-foreground)]">
          {searchQuery || scopeFilter !== SCOPE_FILTER_ALL ? (
            <p>{t("noResults")}</p>
          ) : (
            <div className="space-y-2">
              <p>{t("empty.title")}</p>
              <p className="text-sm">{t("empty.subtitle")}</p>
            </div>
          )}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredDocuments.map((document) => (
            <DocumentCard
              key={document.id}
              document={document}
              onDelete={() => onDeleteDocument(document.id)}
              onRetry={
                onRetryDocument ? () => onRetryDocument(document.id) : undefined
              }
              retrying={retryingIds.has(document.id)}
              retryFailed={retryFailedIds.has(document.id)}
              onChangeScope={
                onChangeScope
                  ? (scope) => onChangeScope(document.id, scope)
                  : undefined
              }
              changingScope={changingScopeIds.has(document.id)}
              scopeChangeFailed={scopeChangeFailedIds.has(document.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
