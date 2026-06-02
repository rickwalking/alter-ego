"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import {
  NeonCard,
  NeonCardContent,
  NeonCardHeader,
  NeonCardTitle,
} from "@/components/molecules/neon-card";
import { NeonInput } from "@/components/atoms/neon-input";
import { NeonSpinner } from "@/components/atoms/neon-spinner";
import { NeonTextarea } from "@/components/atoms/neon-textarea";
import { AiSuggestionPanel } from "@/features/blog/components/ai-suggestion-panel";
import { RichTextEditor } from "@/features/blog/components/rich-text-editor";
import {
  VersionHistorySidebar,
  type BlogPostVersion,
} from "@/features/blog/components/version-history-sidebar";
import { useBlogPosts } from "@/features/blog/hooks/use-blog-posts";
import { ROUTE_PATHS } from "@/constants/api";

export default function BlogPostEditPage() {
  const params = useParams<{ id: string }>();
  const postId = params.id;
  const router = useRouter();
  const t = useTranslations("dashboard.blogPosts");
  const { posts, loading, update, refetch } = useBlogPosts();
  const [title, setTitle] = useState("");
  const [excerpt, setExcerpt] = useState("");
  const [bodyText, setBodyText] = useState("");
  const [selectedText, setSelectedText] = useState("");
  const [lockVersion, setLockVersion] = useState(1);
  const [saving, setSaving] = useState(false);

  const post = posts.find((item) => item.id === postId);

  useEffect(() => {
    void refetch();
  }, [refetch]);

  useEffect(() => {
    if (!post) {
      return;
    }
    setTitle(post.title);
    setExcerpt(post.excerpt ?? "");
    const body =
      typeof post.content?.body === "string" ? post.content.body : "";
    setBodyText(body);
    setLockVersion(post.lock_version ?? 1);
  }, [post]);

  const handleSave = async () => {
    if (!postId) {
      return;
    }
    setSaving(true);
    try {
      await update(
        postId,
        {
          title,
          excerpt,
          content: { body: bodyText },
        },
        lockVersion,
      );
      await refetch();
    } finally {
      setSaving(false);
    }
  };

  const handleRestore = (version: BlogPostVersion) => {
    setTitle(version.title);
    setExcerpt(version.excerpt ?? "");
    const body =
      typeof version.snapshot?.body === "string" ? version.snapshot.body : "";
    setBodyText(body);
  };

  if (loading && !post) {
    return (
      <div className="flex h-64 items-center justify-center">
        <NeonSpinner className="h-8 w-8" />
      </div>
    );
  }

  if (!post) {
    return (
      <div className="container mx-auto py-8 px-4">
        <p>{t("notFound")}</p>
        <Link href={ROUTE_PATHS.BLOG_POSTS}>
          <NeonButton variant="outline" className="mt-4">
            {t("backToList")}
          </NeonButton>
        </Link>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="mb-6 flex items-center justify-between gap-4">
        <h1 className="text-2xl font-bold">{t("editPost")}</h1>
        <div className="flex gap-2">
          <NeonButton
            variant="outline"
            onClick={() => router.push(ROUTE_PATHS.BLOG_POSTS)}
          >
            {t("backToList")}
          </NeonButton>
          <NeonButton onClick={() => void handleSave()} disabled={saving}>
            {saving ? t("saving") : t("saveChanges")}
          </NeonButton>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <NeonCard className="lg:col-span-2">
          <NeonCardHeader>
            <NeonCardTitle>{post.title}</NeonCardTitle>
          </NeonCardHeader>
          <NeonCardContent className="space-y-4">
            <NeonInput
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
            <NeonTextarea
              value={excerpt}
              onChange={(e) => setExcerpt(e.target.value)}
              rows={2}
            />
            <RichTextEditor
              value={bodyText}
              onChange={setBodyText}
              onSelectionChange={setSelectedText}
              placeholder={t("fields.content")}
            />
          </NeonCardContent>
        </NeonCard>

        <div className="space-y-4">
          <VersionHistorySidebar
            postId={postId}
            currentBody={bodyText}
            onRestore={handleRestore}
          />
          <AiSuggestionPanel
            postId={postId}
            selectedText={selectedText}
            onApplySuggestion={setBodyText}
          />
        </div>
      </div>
    </div>
  );
}
