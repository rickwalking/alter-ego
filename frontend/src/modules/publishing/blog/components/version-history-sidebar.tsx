"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { NeonBadge } from "@/components/atoms/neon-badge";
import { NeonButton } from "@/components/atoms/neon-button";
import {
  NeonCard,
  NeonCardContent,
  NeonCardHeader,
  NeonCardTitle,
} from "@/components/molecules/neon-card";
import { API_ENDPOINTS } from "@/constants/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import type { BlogPostVersion, VersionHistorySidebarProps } from "./types";

export function VersionHistorySidebar({
  postId,
  currentBody,
  onRestore,
}: VersionHistorySidebarProps): React.JSX.Element {
  const t = useTranslations("dashboard.blogPosts.versions");
  const [versions, setVersions] = useState<BlogPostVersion[]>([]);
  const [selected, setSelected] = useState<BlogPostVersion | null>(null);
  const [loading, setLoading] = useState(false);

  const loadVersions = useCallback(async () => {
    setLoading(true);
    try {
      const response = await authenticatedFetch(
        API_ENDPOINTS.BLOG_POST_VERSIONS(postId),
      );
      if (!response.ok) {
        return;
      }
      const data = (await response.json()) as BlogPostVersion[];
      setVersions(data);
    } finally {
      setLoading(false);
    }
  }, [postId]);

  useEffect(() => {
    void loadVersions();
  }, [loadVersions]);

  const selectedBody =
    typeof selected?.snapshot?.body === "string" ? selected.snapshot.body : "";

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
          {versions.map((version) => (
            <li key={version.version_number}>
              <button
                type="button"
                className="flex w-full items-center justify-between rounded border px-2 py-1 text-left text-sm hover:bg-muted/50"
                onClick={() => setSelected(version)}
              >
                <span>
                  {t("versionLabel", { number: version.version_number })}
                </span>
                <NeonBadge variant="outline">{version.title}</NeonBadge>
              </button>
            </li>
          ))}
        </ul>
        {selected && (
          <div className="space-y-2 rounded border p-2 text-xs">
            <p className="font-medium">{t("diffTitle")}</p>
            <p className="text-muted-foreground whitespace-pre-wrap">
              {selectedBody.slice(0, 400)}
              {selectedBody.length > 400 ? "…" : ""}
            </p>
            <p className="text-muted-foreground whitespace-pre-wrap">
              {currentBody.slice(0, 400)}
              {currentBody.length > 400 ? "…" : ""}
            </p>
            <NeonButton
              size="sm"
              variant="outline"
              onClick={() => onRestore(selected)}
            >
              {t("restore")}
            </NeonButton>
          </div>
        )}
      </NeonCardContent>
    </NeonCard>
  );
}
