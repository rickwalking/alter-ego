"use client";

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
import {
  AiSuggestionPanel,
  RichTextEditor,
  VersionHistorySidebar,
  useBlogPostEditor,
} from "@/modules/publishing";
import { ROUTE_PATHS } from "@/constants/api";

export default function BlogPostEditPage() {
  const params = useParams<{ id: string }>();
  const postId = params.id;
  const router = useRouter();
  const t = useTranslations("dashboard.blogPosts");
  const {
    post,
    loading,
    saving,
    title,
    setTitle,
    excerpt,
    setExcerpt,
    bodyText,
    setBodyText,
    setSelectedText,
    selectedText,
    handleSave,
    handleRestore,
  } = useBlogPostEditor(postId);

  // AE-0296: saving returns to the listing so the refreshed card is visible.
  const handleSaveAndReturn = async (): Promise<void> => {
    await handleSave();
    router.push(ROUTE_PATHS.BLOG_POSTS);
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
          <NeonButton
            onClick={() => void handleSaveAndReturn()}
            disabled={saving}
          >
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
