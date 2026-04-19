"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Search, Plus, Upload } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { type Document } from "@/schemas/knowledge";
import { DocumentCard } from "./document-card";

interface DocumentListProps {
  documents: Document[];
  isLoading?: boolean;
  onCreateNew: () => void;
  onUploadNew: () => void;
  onDeleteDocument: (id: string) => void;
}

export function DocumentList({
  documents,
  isLoading,
  onCreateNew,
  onUploadNew,
  onDeleteDocument,
}: DocumentListProps) {
  const t = useTranslations("knowledge");
  const [searchQuery, setSearchQuery] = useState("");

  const filteredDocuments = documents.filter(
    (doc) => {
      const meta = doc.metadata as Record<string, unknown> | undefined;
      const tags = (meta?.tags as string[] | undefined) ?? [];
      return (
        doc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        doc.status.toLowerCase().includes(searchQuery.toLowerCase()) ||
        tags.some((tag) => tag.toLowerCase().includes(searchQuery.toLowerCase()))
      );
    }
  );

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="h-40 animate-pulse rounded-lg bg-[var(--color-muted)]"
          />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--color-muted-foreground)]" />
          <Input
            placeholder={t("search")}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
        <Button onClick={onUploadNew} variant="outline" className="gap-2">
          <Upload className="h-4 w-4" />
          {t("uploadButton")}
        </Button>
        <Button onClick={onCreateNew} className="gap-2">
          <Plus className="h-4 w-4" />
          {t("newDocument")}
        </Button>
      </div>

      {filteredDocuments.length === 0 ? (
        <div className="text-center py-12 text-[var(--color-muted-foreground)]">
          {searchQuery ? (
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
            />
          ))}
        </div>
      )}
    </div>
  );
}
