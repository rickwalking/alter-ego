"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Alert, AlertDescription, Badge, Button, Textarea } from "@/components/ui";
import { VOICE_MATCH_MIN_SCORE } from "@/constants/blog-ai";
import { API_ENDPOINTS, HTTP_METHODS } from "@/constants/api";
import type { VoiceScoreResult } from "@/features/blog/types-ai";
import { authenticatedFetch } from "@/lib/authenticated-fetch";

interface VoiceMatchScorerProps {
  personaId: string;
}

export function VoiceMatchScorer({ personaId }: VoiceMatchScorerProps): React.JSX.Element {
  const t = useTranslations("blogEditorial");
  const [text, setText] = useState("");
  const [result, setResult] = useState<VoiceScoreResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const scoreText = async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const response = await authenticatedFetch(API_ENDPOINTS.PERSONA_VOICE_SCORE(personaId), {
        method: HTTP_METHODS.POST,
        body: JSON.stringify({ text }),
      });
      if (!response.ok) {
        throw new Error("Voice scoring failed");
      }
      setResult((await response.json()) as VoiceScoreResult);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Voice scoring failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-3 rounded-lg border p-4">
      <h3 className="font-semibold">{t("voiceScorerTitle")}</h3>
      <Textarea value={text} onChange={(event) => setText(event.target.value)} rows={4} />
      <Button disabled={loading || !text.trim()} onClick={() => void scoreText()}>
        {t("actions.scoreVoice")}
      </Button>
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      {result && (
        <div className="space-y-2">
          <Badge variant={result.overall >= VOICE_MATCH_MIN_SCORE ? "default" : "destructive"}>
            {t("voiceScore", { score: Math.round(result.overall) })}
          </Badge>
          <ul className="text-sm text-muted-foreground space-y-1">
            {result.suggestions.map((suggestion) => (
              <li key={suggestion}>{suggestion}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
