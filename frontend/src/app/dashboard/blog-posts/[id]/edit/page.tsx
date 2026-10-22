"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonSpinner } from "@/components/atoms/neon-spinner";
import { useBlogPostEditor } from "@/modules/publishing";
import { ROUTE_PATHS } from "@/constants/api";
import { BlogPostEditorView } from "@/app/dashboard/blog-posts/[id]/edit/blog-post-editor-view";

/** Blog post editor route: loading / not-found states, then the editor. */
export default function BlogPostEditPage() {
  const params = useParams<{ id: string }>();
  const t = useTranslations("dashboard.blogPosts");
  const editor = useBlogPostEditor(params.id);

  if (editor.loading && !editor.post) {
    return (
      <div className="flex h-64 items-center justify-center">
        <NeonSpinner className="h-8 w-8" />
      </div>
    );
  }

  if (!editor.post) {
    return (
      <div
        className="container mx-auto py-8 px-4"
        role={editor.loadFailed ? "alert" : undefined}
      >
        <h1 className="text-lg font-semibold">
          {editor.loadFailed ? t("errors.loadPostFailed") : t("notFound")}
        </h1>
        <Link href={ROUTE_PATHS.BLOG_POSTS}>
          <NeonButton variant="outline" className="mt-4">
            {t("backToList")}
          </NeonButton>
        </Link>
      </div>
    );
  }

  return <BlogPostEditorView editor={editor} />;
}
