"use client";

import { FileText, Trash2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { type Document } from "@/schemas/knowledge";
import { formatDate } from "@/lib/utils";

interface DocumentCardProps {
  document: Document;
  onDelete?: () => void;
}

export function DocumentCard({ document, onDelete }: DocumentCardProps) {
  const meta = document.metadata as Record<string, unknown> | undefined;
  const tags = (meta?.tags as string[] | undefined) ?? [];
  const statusColors: Record<string, string> = {
    completed: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
    processing: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
    pending: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
    failed: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
  };

  return (
    <Card className="transition-shadow hover:shadow-md">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3 flex-1 min-w-0">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[var(--color-primary)]/10 text-[var(--color-primary)]">
              <FileText className="h-5 w-5" aria-hidden="true" />
            </div>
            <div className="flex-1 min-w-0">
              <CardTitle className="text-lg truncate">{document.title}</CardTitle>
              <div className="flex items-center gap-2 text-xs text-[var(--color-muted-foreground)] mt-1">
                <span>{formatDate(document.created_at)}</span>
                <span>·</span>
                <span>{document.chunk_count} chunks</span>
              </div>
            </div>
          </div>
          {onDelete && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onDelete();
              }}
              className="shrink-0 rounded-md p-1.5 text-[var(--color-muted-foreground)] hover:bg-[var(--color-destructive)]/10 hover:text-[var(--color-destructive)] transition-colors"
              aria-label={`Delete document: ${document.title}`}
            >
              <Trash2 className="h-4 w-4" aria-hidden="true" />
            </button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-2 mb-3">
          <Badge
            variant="secondary"
            className={`text-xs ${statusColors[document.status] ?? ""}`}
          >
            {document.status}
          </Badge>
          {document.error_message && (
            <span className="text-xs text-[var(--color-destructive)] truncate">
              {document.error_message}
            </span>
          )}
        </div>
        {tags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {tags.map((tag) => (
              <Badge key={tag} variant="secondary" className="text-xs">
                {tag}
              </Badge>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
