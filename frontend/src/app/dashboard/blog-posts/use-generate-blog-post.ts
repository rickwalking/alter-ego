"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";
import {
  GENERATION_TOPIC_MAX_CHARS,
  GENERATION_TOPIC_MIN_CHARS,
  generateStandaloneBlogPost,
} from "@/modules/publishing";

interface UseGenerateBlogPostResult {
  open: boolean;
  topic: string;
  pending: boolean;
  failed: boolean;
  canSubmit: boolean;
  show: () => void;
  hide: () => void;
  setTopic: (topic: string) => void;
  submit: () => Promise<void>;
}

/**
 * Standalone "Generate with AI": a topic becomes a draft
 * written in the owner's voice; the editor opens on it while it generates.
 */
export function useGenerateBlogPost(): UseGenerateBlogPostResult {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [topic, setTopic] = useState("");
  const [pending, setPending] = useState(false);
  const [failed, setFailed] = useState(false);
  const trimmed = topic.trim();
  const canSubmit =
    !pending &&
    trimmed.length >= GENERATION_TOPIC_MIN_CHARS &&
    trimmed.length <= GENERATION_TOPIC_MAX_CHARS;

  const submit = async (): Promise<void> => {
    setPending(true);
    setFailed(false);
    try {
      const result = await generateStandaloneBlogPost(trimmed);
      router.push(DASHBOARD_ROUTES.BLOG_POST_EDIT(result.id));
    } catch {
      setFailed(true);
      setPending(false);
    }
  };

  return {
    open,
    topic,
    pending,
    failed,
    canSubmit,
    show: () => setOpen(true),
    hide: () => setOpen(false),
    setTopic,
    submit,
  };
}
