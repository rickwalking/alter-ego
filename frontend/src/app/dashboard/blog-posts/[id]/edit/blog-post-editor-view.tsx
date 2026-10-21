"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import {
  BlogGenerationStatus,
  BlogSectionEditor,
  EditorErrorNotice,
  MigrationBanner,
  isGenerationInProgress,
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
import { BlogPostEditFields } from "@/app/dashboard/blog-posts/[id]/edit/blog-post-edit-fields";
import { BlogEditorSidebar } from "@/app/dashboard/blog-posts/[id]/edit/blog-editor-sidebar";
import type { BlogPostEditorViewProps } from "@/app/dashboard/blog-posts/types";

type EditorProp = BlogPostEditorViewProps["editor"];

/** The id + lock version the editor data loads for ("" / 0 before a post). */
function editorDataKey(post: EditorProp["post"]): [string, number] {
  return [post?.id ?? "", post?.lock_version ?? 0];
}

/** Title, unsaved badge, back and save. */
function EditorHeader({
  editor,
  saveBlocked,
  onLeave,
}: {
  editor: EditorProp;
  saveBlocked: boolean;
  onLeave: () => void;
}): React.ReactElement {
  const t = useTranslations(BLOG_EDITOR_I18N_NAMESPACE);
  return (
    <div className="mb-6 flex items-center justify-between gap-4">
      <h1 className="text-2xl font-bold">{t("heading")}</h1>
      <div className="flex items-center gap-2">
        {editor.dirty && (
          <span className="text-xs text-text-muted">{t("unsaved.badge")}</span>
        )}
        <NeonButton variant="outline" onClick={onLeave}>
          {t("back")}
        </NeonButton>
        <NeonButton
          onClick={() => void editor.handleSave()}
          disabled={editor.saving || !editor.dirty || saveBlocked}
        >
          {editor.saving ? t("saving") : t("save")}
        </NeonButton>
      </div>
    </div>
  );
}

/** Generation progress, the migration banner, or the editor error. */
function EditorNotices({
  editor,
  migrationPending,
}: {
  editor: EditorProp;
  migrationPending: boolean;
}): React.ReactElement {
  const { post, error } = editor;
  return (
    <>
      {post && (
        <BlogGenerationStatus postId={post.id} unsavedChanges={editor.dirty} />
      )}
      {migrationPending && <MigrationBanner detail={error?.detail ?? null} />}
      {error && !migrationPending && <EditorErrorNotice error={error} />}
    </>
  );
}

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
  const data = useBlogEditorData(...editorDataKey(post));
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
  // AE-0425: the writer/image run owns the document until it finishes.
  const generating = isGenerationInProgress(post ?? null);
  const leave = (): void => {
    if (confirmLeave()) {
      router.push(ROUTE_PATHS.BLOG_POSTS);
    }
  };

  return (
    <div className="container mx-auto py-8 px-4">
      <EditorHeader
        editor={editor}
        saveBlocked={migrationPending || generating}
        onLeave={leave}
      />
      <EditorNotices editor={editor} migrationPending={migrationPending} />
      {draft && validation && (
        <fieldset
          disabled={generating}
          aria-busy={generating}
          data-testid="blog-editor-fields"
          className="m-0 min-w-0 border-0 p-0 disabled:opacity-60"
        >
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
        </fieldset>
      )}
    </div>
  );
}
