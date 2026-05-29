"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { NeonBadge } from "@/components/atoms/neon-badge";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonCard, NeonCardContent, NeonCardHeader, NeonCardTitle } from "@/components/molecules/neon-card";
import {
  SEO_PREVIEW_GOOGLE,
  SEO_PREVIEW_LINKEDIN,
  SEO_PREVIEW_TWITTER,
  type SeoPreviewPlatform,
} from "@/constants/seo";
import { useSeoAnalysis } from "@/features/blog/hooks/use-seo-analysis";
import { SITE_URL } from "@/constants/api";

interface SeoPreviewProps {
  postId: string | null;
  title: string;
  slug: string;
  metaTitle?: string;
  metaDescription?: string;
  excerpt?: string;
  featuredImageUrl?: string | null;
}

export function SeoPreview({
  postId,
  title,
  slug,
  metaTitle,
  metaDescription,
  excerpt,
  featuredImageUrl,
}: SeoPreviewProps) {
  const t = useTranslations("blogEditorial.seo");
  const [platform, setPlatform] =
    useState<SeoPreviewPlatform>(SEO_PREVIEW_GOOGLE);
  const { result, loading, analyze } = useSeoAnalysis(postId);

  const displayTitle = metaTitle || title;
  const displayDescription = metaDescription || excerpt || "";
  const url = `${SITE_URL}/blog/${slug}`;

  const tabs: SeoPreviewPlatform[] = [
    SEO_PREVIEW_GOOGLE,
    SEO_PREVIEW_TWITTER,
    SEO_PREVIEW_LINKEDIN,
  ];

  return (
    <NeonCard>
      <NeonCardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <NeonCardTitle className="text-sm">{t("title")}</NeonCardTitle>
          {postId && (
            <NeonButton
              size="sm"
              variant="outline"
              onClick={() => void analyze()}
              disabled={loading}
            >
              {loading ? t("analyzing") : t("analyze")}
            </NeonButton>
          )}
        </div>
        <div role="tablist" className="flex gap-2 mt-2">
          {tabs.map((tab) => (
            <button
              key={tab}
              role="tab"
              aria-selected={platform === tab}
              className={`text-xs px-2 py-1 rounded ${platform === tab ? "bg-primary text-primary-foreground" : "bg-muted"}`}
              onClick={() => setPlatform(tab)}
            >
              {t(`platform.${tab}`)}
            </button>
          ))}
        </div>
      </NeonCardHeader>
      <NeonCardContent className="space-y-3">
        {platform === SEO_PREVIEW_GOOGLE && (
          <div className="rounded border p-3 space-y-1">
            <p className="text-blue-600 text-sm truncate">{url}</p>
            <p className="text-lg text-blue-800 font-medium truncate">
              {displayTitle}
            </p>
            <p className="text-sm text-gray-600 line-clamp-2">
              {displayDescription}
            </p>
          </div>
        )}
        {platform === SEO_PREVIEW_TWITTER && (
          <div className="rounded border p-3 space-y-2">
            {featuredImageUrl && (
              <img
                src={featuredImageUrl}
                alt=""
                className="w-full h-32 object-cover rounded"
              />
            )}
            <p className="font-medium truncate">{displayTitle}</p>
            <p className="text-sm text-muted-foreground line-clamp-2">
              {displayDescription}
            </p>
          </div>
        )}
        {platform === SEO_PREVIEW_LINKEDIN && (
          <div className="rounded border p-3 space-y-1">
            <p className="font-medium truncate">{displayTitle}</p>
            <p className="text-xs text-muted-foreground truncate">{url}</p>
            <p className="text-sm line-clamp-3">{displayDescription}</p>
          </div>
        )}
        {result && (
          <div className="flex items-center gap-2">
            <NeonBadge variant={result.passed ? "default" : "destructive"}>
              {t("score", { score: result.overall_score })}
            </NeonBadge>
            <span className="text-xs text-muted-foreground">
              {result.severity}
            </span>
          </div>
        )}
        {result?.suggestions.map((s) => (
          <p key={s} className="text-xs text-amber-700">
            {s}
          </p>
        ))}
      </NeonCardContent>
    </NeonCard>
  );
}
