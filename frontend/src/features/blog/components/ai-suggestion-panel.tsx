"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Alert, AlertDescription, Badge, Button, Textarea } from "@/components/ui";
import { BLOG_AI_ACTIONS, VOICE_MATCH_MIN_SCORE } from "@/constants/blog-ai";
import { useBlogAi } from "@/features/blog/hooks/use-blog-ai";
import type { BlogAiSuggestResult } from "@/features/blog/types-ai";

interface AiSuggestionPanelProps {
  postId: string;
  selectedText: string;
  onApplySuggestion: (text: string) => void;
  personaId?: string;
}

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
    const result = await improve(selectedText, BLOG_AI_ACTIONS.IMPROVE, undefined, personaId);
    onApplySuggestion(result.improved_text);
  };

  return (
    <div className="space-y-4 rounded-lg border p-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">{t("aiPanelTitle")}</h3>
        {voiceScore !== null && (
          <Badge variant={voiceScore >= VOICE_MATCH_MIN_SCORE ? "default" : "destructive"}>
            {t("voiceScore", { score: Math.round(voiceScore) })}
          </Badge>
        )}
      </div>

      {!selectedText.trim() && (
        <Alert>
          <AlertDescription>{t("selectTextHint")}</AlertDescription>
        </Alert>
      )}

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="flex flex-wrap gap-2">
        <Button size="sm" disabled={loading || !selectedText.trim()} onClick={() => void runSuggestion(BLOG_AI_ACTIONS.IMPROVE)}>
          {t("actions.improve")}
        </Button>
        <Button size="sm" variant="outline" disabled={loading || !selectedText.trim()} onClick={() => void runSuggestion(BLOG_AI_ACTIONS.SHORTEN)}>
          {t("actions.shorten")}
        </Button>
        <Button size="sm" variant="outline" disabled={loading || !selectedText.trim()} onClick={() => void runSuggestion(BLOG_AI_ACTIONS.ADD_OPINION)}>
          {t("actions.addOpinion")}
        </Button>
        <Button size="sm" variant="secondary" disabled={loading || !selectedText.trim()} onClick={() => void runImprove()}>
          {t("actions.applyImprovement")}
        </Button>
      </div>

      <div className="space-y-3">
        {suggestions.map((item, index) => (
          <div key={`${item.suggestion_type}-${index}`} className="rounded-md bg-muted p-3 space-y-2">
            <div className="flex items-center justify-between">
              <Badge variant="secondary">{item.suggestion_type}</Badge>
              <Button size="sm" onClick={() => onApplySuggestion(item.suggested_text)}>
                {t("actions.apply")}
              </Button>
            </div>
            <Textarea value={item.suggested_text} readOnly rows={3} />
            {item.explanation && <p className="text-sm text-muted-foreground">{item.explanation}</p>}
          </div>
        ))}
      </div>
    </div>
  );
}
