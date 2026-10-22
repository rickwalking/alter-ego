"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { CaptionEditor, countHashtags } from "./caption-editor";
import { CopySaveBar } from "./copy-save-bar";
import { LanguageTabs } from "./publish-panel-parts";
import { LeaveGuardDialog } from "./leave-guard-dialog";
import type { ReviewCopyEditorProps } from "./types";
import type { CopyField } from "@/modules/publishing/distribution/hooks/types";
import { useLeaveGuard } from "@/modules/publishing/distribution/hooks/use-leave-guard";
import { COPY_FIELDS } from "@/modules/publishing/distribution/lib/copy-editor-state";
import {
  IG_MAX_CHARS,
  IG_MAX_HASHTAGS,
  LINKEDIN_MAX_CHARS,
  captionInvalid,
  linkedinInvalid,
} from "@/modules/publishing/distribution/lib/copy-limits";
import type { ViewerLanguage } from "@/modules/publishing/distribution/types";

const CAPTION_ONLY: readonly CopyField[] = ["caption"];
const LINKEDIN_POSTS: readonly CopyField[] = ["linkedinPt", "linkedinEn"];

/**
 * The Instagram caption editor of a review step: the publish page's limits and
 * save bar, without copy or publish (those stay on the publish page).
 */
export function ReviewCaptionEditor({
  editor,
}: Readonly<ReviewCopyEditorProps>): React.ReactElement {
  const t = useTranslations("publish");
  const caption = editor.draft.caption;
  return (
    <div className="space-y-3">
      <CaptionEditor
        value={caption}
        onChange={(text) => editor.setText("caption", text)}
        maxChars={IG_MAX_CHARS}
        placeholder={t("instagram.placeholder")}
        ariaLabel={t("instagram.captionLabel")}
        helpText={t("instagram.hashtagHelp", {
          count: countHashtags(caption),
          max: IG_MAX_HASHTAGS,
        })}
      />
      <CopySaveBar
        dirty={editor.isDirty(CAPTION_ONLY)}
        status={editor.status}
        invalid={captionInvalid(caption)}
        onSave={() => editor.save(CAPTION_ONLY)}
      />
    </div>
  );
}

/** The PT / EN LinkedIn post editor of a review step, saved per language. */
export function ReviewLinkedInEditor({
  editor,
}: Readonly<ReviewCopyEditorProps>): React.ReactElement {
  const t = useTranslations("publish");
  const [language, setLanguage] = useState<ViewerLanguage>("pt");
  const field: CopyField = language === "pt" ? "linkedinPt" : "linkedinEn";
  const text = editor.draft[field];
  return (
    <div className="space-y-3">
      <LanguageTabs
        language={language}
        onChange={setLanguage}
        ariaLabel={t("linkedin.languageTabsLabel")}
        className="flex gap-1"
      />
      <CaptionEditor
        value={text}
        onChange={(next) => editor.setText(field, next)}
        maxChars={LINKEDIN_MAX_CHARS}
        placeholder={t("linkedin.placeholder")}
        ariaLabel={t("linkedin.postLabel", {
          language: language.toUpperCase(),
        })}
        helpText={t("linkedin.help")}
      />
      <CopySaveBar
        dirty={editor.isDirty(LINKEDIN_POSTS)}
        status={editor.status}
        invalid={linkedinInvalid(text)}
        onSave={() => editor.save(LINKEDIN_POSTS)}
      />
    </div>
  );
}

/** Asks before an in-app link drops unsaved review-step edits. */
export function ReviewCopyLeaveGuard({
  editor,
}: Readonly<ReviewCopyEditorProps>): React.ReactElement | null {
  const guard = useLeaveGuard(editor.canSave && editor.isDirty(COPY_FIELDS));
  return <LeaveGuardDialog guard={guard} />;
}
