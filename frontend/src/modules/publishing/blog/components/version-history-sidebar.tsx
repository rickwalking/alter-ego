"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { NeonBadge } from "@/components/atoms/neon-badge";
import { NeonButton } from "@/components/atoms/neon-button";
import {
  NeonCard,
  NeonCardContent,
  NeonCardHeader,
  NeonCardTitle,
} from "@/components/molecules/neon-card";
import { tryParseBlogContent } from "../lib/parse-blog-content";
import { EditorErrorNotice } from "./editor-error-notice";
import type { BlogPostVersion, VersionHistorySidebarProps } from "./types";
import type { BlogEditorError } from "../types";

const PREVIEW_CHARS = 400;
const PARAGRAPH_BREAK = "\n\n";

/** The text of a `blog.v2` snapshot (sections joined), for the diff preview. */
export function snapshotText(snapshot: BlogPostVersion["snapshot"]): string {
  const document = tryParseBlogContent(snapshot);
  if (!document) {
    return "";
  }
  return document.sections
    .map((section) =>
      [section.heading, section.body_md].filter(Boolean).join(PARAGRAPH_BREAK),
    )
    .join(PARAGRAPH_BREAK);
}

function clip(text: string): string {
  return text.length > PREVIEW_CHARS
    ? `${text.slice(0, PREVIEW_CHARS)}…`
    : text;
}

/**
 * Version history of a post: every save appends a snapshot,
 * listed here newest first; restoring calls the restore route (a new snapshot records it)
 * and loads the restored content into the editor. A failed restore shows its
 * error inline.
 */
export function VersionHistorySidebar({
  versions,
  loading,
  currentText,
  disabled,
  onRestore,
}: Readonly<VersionHistorySidebarProps>): React.JSX.Element {
  const t = useTranslations("dashboard.blogPosts.versions");
  const [selected, setSelected] = useState<BlogPostVersion | null>(null);
  const [restoreError, setRestoreError] = useState<BlogEditorError | null>(
    null,
  );
  const newestFirst = [...versions].sort(
    (a, b) => b.version_number - a.version_number,
  );
  const restore = async (versionNumber: number): Promise<void> => {
    setRestoreError(null);
    const error = await onRestore(versionNumber);
    if (error) {
      setRestoreError(error);
    }
  };
  return (
    <NeonCard>
      <NeonCardHeader className="pb-2">
        <NeonCardTitle className="text-base">{t("title")}</NeonCardTitle>
      </NeonCardHeader>
      <NeonCardContent className="space-y-3">
        {loading && (
          <p className="text-muted-foreground text-sm">{t("loading")}</p>
        )}
        {!loading && versions.length === 0 && (
          <p className="text-muted-foreground text-sm">{t("empty")}</p>
        )}
        <ul className="max-h-48 space-y-2 overflow-auto">
          {newestFirst.map((version) => (
            <li key={version.version_number}>
              <button
                type="button"
                className="flex w-full items-center justify-between rounded border px-2 py-1 text-left text-sm hover:bg-muted/50"
                onClick={() => setSelected(version)}
              >
                <span>
                  {t("versionLabel", { number: version.version_number })}
                </span>
                {version.title && (
                  <NeonBadge variant="outline">{version.title}</NeonBadge>
                )}
              </button>
            </li>
          ))}
        </ul>
        {selected && (
          <div className="space-y-2 rounded border p-2 text-xs">
            <p className="font-medium">{t("diffTitle")}</p>
            <p className="text-muted-foreground whitespace-pre-wrap">
              {clip(snapshotText(selected.snapshot))}
            </p>
            <p className="text-muted-foreground whitespace-pre-wrap">
              {clip(currentText)}
            </p>
            <NeonButton
              size="sm"
              variant="outline"
              disabled={disabled}
              onClick={() => void restore(selected.version_number)}
            >
              {t("restore")}
            </NeonButton>
          </div>
        )}
        <EditorErrorNotice error={restoreError} />
      </NeonCardContent>
    </NeonCard>
  );
}
