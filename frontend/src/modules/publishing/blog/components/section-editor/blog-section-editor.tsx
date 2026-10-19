"use client";

import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { BLOG_EDITOR_I18N_NAMESPACE } from "@/constants/blog-editor";
import { BLOG_COVER_ISSUE_KEY } from "../../editor-content";
import {
  imageSlotKey,
  rewriteSlotKey,
  TRANSLATION_SLOT_KEY,
} from "../../hooks/use-blog-editor-actions";
import {
  activeDocument,
  addSection,
  BLOG_CONTENT_EN,
  deleteSection,
  moveSection,
  setCover,
  updateSection,
} from "../../lib/editor-document";
import { ImageSlot } from "./image-slot";
import { LanguageTabs } from "./language-tabs";
import { SectionCard } from "./section-card";
import type { BlogSectionEditorProps } from "./types";

/**
 * The `blog.v2` section editor (AE-0424): PT/EN content buttons, the cover
 * slot and one card per section of the active language (add / delete /
 * reorder). Only the active language subtree is edited.
 */
export function BlogSectionEditor({
  document,
  language,
  validation,
  statusOf,
  onLanguageChange,
  onDocumentChange,
  onGenerateImage,
  onRewrite,
  onGenerateTranslation,
  onSelectText,
}: BlogSectionEditorProps): React.ReactElement {
  const t = useTranslations(BLOG_EDITOR_I18N_NAMESPACE);
  const current = activeDocument(document, language);
  const hasEnglish = Boolean(document.translations[BLOG_CONTENT_EN]);
  const readOnly = current === null;
  const shown = current ?? document;
  const coverSlot = { language, sectionId: null };
  return (
    <div className="space-y-4">
      <LanguageTabs
        language={language}
        hasEnglish={hasEnglish}
        translationStatus={statusOf(TRANSLATION_SLOT_KEY)}
        onChange={onLanguageChange}
        onGenerateTranslation={onGenerateTranslation}
      />
      <ImageSlot
        key={`${language}-cover`}
        slotId={`${language}-cover`}
        label={t("cover.label")}
        image={shown.cover}
        status={statusOf(imageSlotKey(coverSlot))}
        readOnly={readOnly}
        issue={validation[`${language}:${BLOG_COVER_ISSUE_KEY}`] ?? null}
        onGenerate={(prompt) => onGenerateImage(coverSlot, prompt)}
        onChange={(cover) =>
          onDocumentChange((doc) => setCover(doc, language, cover))
        }
      />
      {shown.sections.map((section, index) => {
        const slot = { language, sectionId: section.id };
        return (
          <SectionCard
            key={`${language}-${section.id}`}
            section={section}
            index={index}
            count={shown.sections.length}
            language={language}
            readOnly={readOnly}
            issue={validation[`${language}:${section.id}`] ?? null}
            imageStatus={statusOf(imageSlotKey(slot))}
            rewriteStatus={statusOf(rewriteSlotKey(slot))}
            onChange={(patch) =>
              onDocumentChange((doc) =>
                updateSection(doc, language, { id: section.id, patch }),
              )
            }
            onMove={(delta) =>
              onDocumentChange((doc) =>
                moveSection(doc, language, { id: section.id, delta }),
              )
            }
            onDelete={() =>
              onDocumentChange((doc) =>
                deleteSection(doc, language, section.id),
              )
            }
            onGenerateImage={(prompt) => onGenerateImage(slot, prompt)}
            onRewrite={() => onRewrite(section.id)}
            onSelectText={(text) =>
              onSelectText({ sectionId: section.id, text })
            }
          />
        );
      })}
      <NeonButton
        variant="outline"
        disabled={readOnly}
        onClick={() => onDocumentChange((doc) => addSection(doc, language))}
      >
        {t("section.add")}
      </NeonButton>
    </div>
  );
}
