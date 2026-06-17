"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  NeonAlert,
  NeonAlertDescription,
} from "@/components/molecules/neon-alert";
import { NeonBadge } from "@/components/atoms/neon-badge";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonTextarea } from "@/components/atoms/neon-textarea";
import { BLOG_AI_ACTIONS, VOICE_MATCH_MIN_SCORE } from "@/constants/blog-ai";
import { useBlogAi } from "@/modules/publishing/blog/hooks/use-blog-ai";
import type { BlogAiSuggestResult } from "@/modules/publishing/blog/types-ai";
import type { AiSuggestionPanelProps } from "./types";

export function AiSuggestionPanel({
  postId,
  selectedText,
  onApplySuggestion,
  personaId,
}: AiSuggestionPanelProps): React.JSX.Element {
  const t = useTranslations("blogEditorial");
  const { suggest, improve, scoreVoice, loading, error } = useBlogAi(postId);
  const [suggestions, setSuggestions] = useState<BlogAiSuggestResult[]>([]);
  const [voiceScore, setVoiceScore] = useState<number | null>(null);

  const runSuggestion = async (action: string): Promise<void> => {
    if (!selectedText.trim()) {
      return;
    }
    const result = await suggest(selectedText, action);
    setSuggestions((prev) => [result, ...prev]);
    if (personaId) {
      const score = await scoreVoice(personaId, result.suggested_text);
      setVoiceScore(score.overall);
    }
  };

  const runImprove = async (): Promise<void> => {
    if (!selectedText.trim()) {
      return;
    }
    const result = await improve({
      text: selectedText,
      action: BLOG_AI_ACTIONS.IMPROVE,
      personaId,
    });
    onApplySuggestion(result.improved_text);
  };

  return (
    <div className="space-y-4 rounded-lg border p-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">{t("aiPanelTitle")}</h3>
        {voiceScore !== null && (
          <NeonBadge
            variant={
              voiceScore >= VOICE_MATCH_MIN_SCORE ? "default" : "destructive"
            }
          >
            {t("voiceScore", { score: Math.round(voiceScore) })}
          </NeonBadge>
        )}
      </div>

      {!selectedText.trim() && (
        <NeonAlert>
          <NeonAlertDescription>{t("selectTextHint")}</NeonAlertDescription>
        </NeonAlert>
      )}

      {error && (
        <NeonAlert variant="destructive">
          <NeonAlertDescription>{error}</NeonAlertDescription>
        </NeonAlert>
      )}

      <div className="flex flex-wrap gap-2">
        <NeonButton
          size="sm"
          disabled={loading || !selectedText.trim()}
          onClick={() => void runSuggestion(BLOG_AI_ACTIONS.IMPROVE)}
        >
          {t("actions.improve")}
        </NeonButton>
        <NeonButton
          size="sm"
          variant="outline"
          disabled={loading || !selectedText.trim()}
          onClick={() => void runSuggestion(BLOG_AI_ACTIONS.SHORTEN)}
        >
          {t("actions.shorten")}
        </NeonButton>
        <NeonButton
          size="sm"
          variant="outline"
          disabled={loading || !selectedText.trim()}
          onClick={() => void runSuggestion(BLOG_AI_ACTIONS.ADD_OPINION)}
        >
          {t("actions.addOpinion")}
        </NeonButton>
        <NeonButton
          size="sm"
          variant="secondary"
          disabled={loading || !selectedText.trim()}
          onClick={() => void runImprove()}
        >
          {t("actions.applyImprovement")}
        </NeonButton>
      </div>

      <div className="space-y-3">
        {suggestions.map((item, index) => (
          <div
            key={`${item.suggestion_type}-${index}`}
            className="rounded-md bg-muted p-3 space-y-2"
          >
            <div className="flex items-center justify-between">
              <NeonBadge variant="secondary">{item.suggestion_type}</NeonBadge>
              <NeonButton
                size="sm"
                onClick={() => onApplySuggestion(item.suggested_text)}
              >
                {t("actions.apply")}
              </NeonButton>
            </div>
            <NeonTextarea value={item.suggested_text} readOnly rows={3} />
            {item.explanation && (
              <p className="text-sm text-muted-foreground">
                {item.explanation}
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
