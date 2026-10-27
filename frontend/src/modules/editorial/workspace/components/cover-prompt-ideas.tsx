"use client";

import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { COVER_IDEA_SOURCES } from "@/constants/cover-prompt-ideas";
import type { CoverPromptIdeasProps } from "./types";

/**
 * Three to six prompt ideas for a new cover photo: tapping one hands it to the
 * prompt field. "Outras ideias" shows a new curated set; "Mais ideias" asks for AI ideas (it needs a topic first).
 */
export function CoverPromptIdeas({
  ideas,
  source,
  onPick,
  onMore,
  onShuffle,
  canAskMore,
  loadingMore,
  moreFailed,
}: Readonly<CoverPromptIdeasProps>): React.ReactElement {
  const t = useTranslations("create.coverIdeas");
  const title =
    source === COVER_IDEA_SOURCES.AI ? t("aiTitle") : t("catalogueTitle");
  return (
    <section aria-label={title} className="flex flex-col gap-2">
      <span className="text-[11px] text-text-muted">{title}</span>
      <ul className="flex flex-col gap-1.5">
        {ideas.map((idea) => (
          <li key={idea}>
            <button
              type="button"
              aria-label={t("use", { idea })}
              onClick={() => onPick(idea)}
              className="w-full rounded-md border border-white/10 bg-white/5 px-2.5 py-1.5 text-left text-xs text-text-primary hover:border-neon-cyan/60"
            >
              {idea}
            </button>
          </li>
        ))}
      </ul>
      <div className="flex flex-wrap items-center gap-2">
        <NeonButton variant="secondary" size="sm" onClick={onShuffle}>
          {t("shuffle")}
        </NeonButton>
        <NeonButton
          variant="secondary"
          size="sm"
          loading={loadingMore}
          disabled={!canAskMore}
          onClick={onMore}
        >
          {t("more")}
        </NeonButton>
        {!canAskMore && (
          <span className="text-[11px] text-text-muted">{t("needsTopic")}</span>
        )}
      </div>
      {moreFailed && (
        <p role="alert" className="text-xs text-red-400">
          {t("moreFailed")}
        </p>
      )}
    </section>
  );
}
