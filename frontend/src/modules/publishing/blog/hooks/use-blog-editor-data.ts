"use client";

/**
 * Read-side data of the blog editor (AE-0424): the version sidebar (re-read
 * whenever a save bumps `lock_version`, so a new snapshot shows up at once)
 * and the voice personas for "Rewrite this section in my voice".
 */

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { fetchVersions, fetchVoicePersonas } from "../blog-editor-requests";
import type { BlogEditorData } from "./types";

export const blogPostVersionsKey = (postId: string, lockVersion: number) =>
  ["blog-post-versions", postId, lockVersion] as const;
export const blogVoicePersonasKey = ["blog-voice-personas"] as const;

export function useBlogEditorData(
  postId: string,
  lockVersion: number,
): BlogEditorData {
  const versions = useQuery({
    queryKey: blogPostVersionsKey(postId, lockVersion),
    queryFn: () => fetchVersions(postId),
    enabled: Boolean(postId),
  });
  const personas = useQuery({
    queryKey: blogVoicePersonasKey,
    queryFn: fetchVoicePersonas,
  });
  const [chosen, setChosen] = useState<string | null>(null);
  const list = personas.data ?? [];
  return {
    versions: versions.data ?? [],
    versionsLoading: versions.isPending,
    personas: list,
    personaId: chosen ?? list[0]?.id ?? null,
    setPersonaId: setChosen,
  };
}
