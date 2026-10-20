"use client";

import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import {
  NeonAlert,
  NeonAlertDescription,
} from "@/components/molecules/neon-alert";
import { BLOG_EDITOR_I18N_NAMESPACE } from "@/constants/blog-editor";
import {
  BLOG_CONTENT_EN,
  BLOG_CONTENT_LANGUAGES,
} from "../../lib/editor-document";
import { EditorErrorNotice } from "../editor-error-notice";
import type { LanguageTabsProps } from "./types";

/**
 * PT / EN content-language buttons (AE-0424). They switch the edited
 * document (`content` vs `content.translations.en`), never the UI locale. A
 * missing EN document is read-only with a "Generate EN translation" action.
 */
export function LanguageTabs({
  language,
  hasEnglish,
  translationStatus,
  onChange,
  onGenerateTranslation,
}: LanguageTabsProps): React.ReactElement {
  const t = useTranslations(BLOG_EDITOR_I18N_NAMESPACE);
  const missingEnglish = language === BLOG_CONTENT_EN && !hasEnglish;
  return (
    <div className="space-y-2">
      <div role="group" aria-label={t("language.label")} className="flex gap-2">
        {BLOG_CONTENT_LANGUAGES.map((lang) => (
          <NeonButton
            key={lang}
            size="sm"
            variant={lang === language ? "primary" : "outline"}
            aria-pressed={lang === language}
            onClick={() => onChange(lang)}
          >
            {t(`language.${lang}`)}
          </NeonButton>
        ))}
      </div>
      {missingEnglish && (
        <NeonAlert>
          <NeonAlertDescription className="space-y-2">
            <span className="block">{t("language.missingEnglish")}</span>
            <NeonButton
              size="sm"
              disabled={translationStatus.pending}
              loading={translationStatus.pending}
              onClick={onGenerateTranslation}
            >
              {t("language.generateEnglish")}
            </NeonButton>
          </NeonAlertDescription>
        </NeonAlert>
      )}
      {missingEnglish && translationStatus.error && (
        <EditorErrorNotice error={translationStatus.error} />
      )}
    </div>
  );
}
