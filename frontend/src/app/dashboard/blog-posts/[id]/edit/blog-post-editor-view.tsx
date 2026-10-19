"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import {
  BlogSectionEditor,
  MigrationBanner,
  applySuggestion,
  useBlogEditorActions,
  useBlogEditorData,
  useBlogReviewActions,
  useUnsavedChangesGuard,
} from "@/modules/publishing";
import type { SectionSelection } from "@/modules/publishing";
import {
  BLOG_EDITOR_ERROR_KINDS,
  BLOG_EDITOR_I18N_NAMESPACE,
} from "@/constants/blog-editor";
import { ROUTE_PATHS } from "@/constants/api";
import { NEON_RED } from "@/constants/neon";
import { BlogPostEditFields } from "@/app/dashboard/blog-posts/[id]/edit/blog-post-edit-fields";
import { BlogEditorSidebar } from "@/app/dashboard/blog-posts/[id]/edit/blog-editor-sidebar";
import type { BlogPostEditorViewProps } from "@/app/dashboard/blog-posts/types";

/**
 * The loaded blog editor (AE-0424): title/excerpt, the `blog.v2` section
 * editor and the review/voice/version/AI sidebar, with the unsaved guard.
 */
export function BlogPostEditorView({
  editor,
}: BlogPostEditorViewProps): React.ReactElement {
  const router = useRouter();
  const t = useTranslations(BLOG_EDITOR_I18N_NAMESPACE);
  const post = editor.post;
  const data = useBlogEditorData(post?.id ?? "", post?.lock_version ?? 0);
  const actions = useBlogEditorActions(editor, data.personaId);
  const review = useBlogReviewActions(editor);
  const { confirmLeave } = useUnsavedChangesGuard(
    editor.dirty,
    t("unsaved.confirm"),
  );
  const [selection, setSelection] = useState<SectionSelection | null>(null);
  const { draft, validation, error } = editor;
  const migrationPending =
    !draft || error?.kind === BLOG_EDITOR_ERROR_KINDS.MIGRATION_PENDING;
  const leave = (): void => {
    if (confirmLeave()) {
      router.push(ROUTE_PATHS.BLOG_POSTS);
    }
  };

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="mb-6 flex items-center justify-between gap-4">
        <h1 className="text-2xl font-bold">{t("heading")}</h1>
        <div className="flex items-center gap-2">
          {editor.dirty && (
            <span className="text-xs text-text-muted">
              {t("unsaved.badge")}
            </span>
          )}
          <NeonButton variant="outline" onClick={leave}>
            {t("back")}
          </NeonButton>
          <NeonButton
            onClick={() => void editor.handleSave()}
            disabled={editor.saving || !editor.dirty || migrationPending}
          >
            {editor.saving ? t("saving") : t("save")}
          </NeonButton>
        </div>
      </div>
      {migrationPending && <MigrationBanner detail={error?.detail ?? null} />}
      {error && !migrationPending && (
        <p className="mb-4 text-sm" style={{ color: NEON_RED }} role="alert">
          {t(`errors.${error.kind}`)}
        </p>
      )}
      {draft && validation && (
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="space-y-4 lg:col-span-2">
            <BlogPostEditFields
              title={draft.title}
              onTitleChange={(title) =>
                editor.updateDraft((d) => ({ ...d, title }))
              }
              excerpt={draft.excerpt}
              onExcerptChange={(excerpt) =>
                editor.updateDraft((d) => ({ ...d, excerpt }))
              }
              validation={validation}
            />
            <BlogSectionEditor
              document={draft.document}
              language={editor.language}
              validation={validation.document}
              statusOf={actions.statusOf}
              onLanguageChange={editor.setLanguage}
              onDocumentChange={(edit) =>
                editor.updateDraft((d) => ({
                  ...d,
                  document: edit(d.document),
                }))
              }
              onGenerateImage={(slot, prompt) =>
                void actions.generateImage(slot, prompt)
              }
              onRewrite={(sectionId) => void actions.rewrite(sectionId)}
              onGenerateTranslation={() => void actions.generateTranslation()}
              onSelectText={setSelection}
            />
          </div>
          <BlogEditorSidebar
            editor={editor}
            review={review}
            data={data}
            selection={selection}
            slotsPending={actions.anyPending}
            onApplySuggestion={(text) =>
              editor.updateDraft((d) => ({
                ...d,
                document: applySuggestion(d.document, {
                  language: editor.language,
                  selection,
                  text,
                }),
              }))
            }
          />
        </div>
      )}
    </div>
  );
}
