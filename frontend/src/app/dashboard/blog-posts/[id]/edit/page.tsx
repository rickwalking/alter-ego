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
import { NeonSpinner } from "@/components/atoms/neon-spinner";
import {
  AiSuggestionPanel,
  VersionHistorySidebar,
  useBlogPostEditor,
} from "@/modules/publishing";
import type { BlogEditorSaveError } from "@/modules/publishing";
import { ROUTE_PATHS } from "@/constants/api";
import { NEON_RED } from "@/constants/neon";
import { BlogPostEditFields } from "@/app/dashboard/blog-posts/[id]/edit/blog-post-edit-fields";

/** i18n key per save failure (AE-0411, B19). */
const SAVE_ERROR_KEYS: Record<BlogEditorSaveError, string> = {
  version_conflict: "errors.saveConflict",
  validation_failed: "errors.saveValidation",
  blog_post_slug_conflict: "errors.slugConflict",
  carousel_origin_delete_blocked: "errors.saveFailed",
  failed: "errors.saveFailed",
};

export default function BlogPostEditPage() {
  const params = useParams<{ id: string }>();
  const postId = params.id;
  const router = useRouter();
  const t = useTranslations("dashboard.blogPosts");
  const {
    post,
    loading,
    loadFailed,
    saving,
    title,
    setTitle,
    excerpt,
    setExcerpt,
    bodyText,
    setBodyText,
    setSelectedText,
    selectedText,
    validation,
    saveError,
    handleSave,
    handleRestore,
  } = useBlogPostEditor(postId);
  const invalid = validation.title !== null || validation.excerpt !== null;

  // AE-0296: saving returns to the listing so the refreshed card is visible.
  // AE-0411: only on success — a failed save stays here and shows the error.
  const handleSaveAndReturn = async (): Promise<void> => {
    if (await handleSave()) {
      router.push(ROUTE_PATHS.BLOG_POSTS);
    }
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
        <p role={loadFailed ? "alert" : undefined}>
          {loadFailed ? t("errors.loadPostFailed") : t("notFound")}
        </p>
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
            disabled={saving || invalid}
          >
            {saving ? t("saving") : t("saveChanges")}
          </NeonButton>
        </div>
      </div>

      {saveError && (
        <p className="mb-4 text-sm" style={{ color: NEON_RED }} role="alert">
          {t(SAVE_ERROR_KEYS[saveError])}
        </p>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <NeonCard className="lg:col-span-2">
          <NeonCardHeader>
            <NeonCardTitle>{post.title}</NeonCardTitle>
          </NeonCardHeader>
          <NeonCardContent className="space-y-4">
            <BlogPostEditFields
              title={title}
              onTitleChange={setTitle}
              excerpt={excerpt}
              onExcerptChange={setExcerpt}
              bodyText={bodyText}
              onBodyChange={setBodyText}
              onSelectionChange={setSelectedText}
              validation={validation}
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
