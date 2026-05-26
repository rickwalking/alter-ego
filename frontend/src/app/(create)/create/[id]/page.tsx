"use client";

import { useCallback, useLayoutEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Header } from "@/components/layout";
import { MessageInput } from "@/features/chat/components";
import { MessageList } from "@/features/chat/components";
import {
  CarouselProgress,
  CarouselPreview,
} from "@/features/create/components";
import { EditorialWorkflowPanel } from "@/features/create/components/editorial-workflow-panel";
import { SourceMaterialViewer } from "@/features/create/components/source-material-viewer";
import {
  useCarouselProject,
  useCarouselStatus,
  useCarouselStream,
  useResumeCarousel,
} from "@/features/create/hooks";
import { useCreateConversation } from "@/features/chat/hooks/use-chat";
import { streamSseEvents, SSE_EVENT_TYPE } from "@/lib/sse-client";
import { API_ENDPOINTS, ROUTE_PATHS } from "@/constants/api";
import { CONVERSATION_METADATA_PROJECT_ID } from "@/constants/publish-chat";
import type { Message } from "@/schemas/chat";
import type { CarouselProjectResponse } from "@/schemas/carousel";

const CONVERSATION_STORAGE_KEY = (projectId: string): string =>
  `alter-ego:conversation:${projectId}`;

export default function WorkspacePage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const t = useTranslations("create");
  const { data: project } = useCarouselProject(projectId);
  const { data: statusData } = useCarouselStatus(projectId);
  // SSE stream writes into the same TanStack Query cache as the polling
  // hook, so progress updates show up in real time; polling stays as a
  // fallback when SSE is blocked (corporate proxies, etc.).
  const stream = useCarouselStream(projectId);
  const resumeCarousel = useResumeCarousel();
  const createConversation = useCreateConversation();
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [carouselComplete, setCarouselComplete] = useState(false);
  const [completedProject, setCompletedProject] =
    useState<CarouselProjectResponse | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const streamingContentRef = useRef("");
  const streamingMsgIdRef = useRef<string | null>(null);

  useLayoutEffect(() => {
    if (!projectId) return;

    const storedId = sessionStorage.getItem(
      CONVERSATION_STORAGE_KEY(projectId),
    );
    if (storedId) {
      setConversationId(storedId);
      return;
    }

    createConversation
      .mutateAsync({
        title: `Carousel: ${project?.topic || projectId}`,
        metadata: { [CONVERSATION_METADATA_PROJECT_ID]: projectId },
      })
      .then((conv) => {
        sessionStorage.setItem(CONVERSATION_STORAGE_KEY(projectId), conv.id);
        setConversationId(conv.id);
      })
      .catch(() => {
        // Silently ignore creation errors (e.g. 429 rate-limit) so the
        // user can still interact with the workspace chat manually.
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  useLayoutEffect(() => {
    if (statusData?.status === "completed" && project) {
      setCarouselComplete(true);
      setCompletedProject(project);
    }
  }, [statusData?.status, project]);

  const handleSendMessage = useCallback(
    (content: string) => {
      if (!content.trim() || !conversationId) return;

      const userMsg: Message = {
        id: `user-${Date.now()}`,
        role: "user",
        content: content.trim(),
        sources: [],
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);

      setIsStreaming(true);
      streamingMsgIdRef.current = null;
      streamingContentRef.current = "";

      if (abortRef.current) {
        abortRef.current.abort();
      }
      abortRef.current = new AbortController();

      streamSseEvents({
        url: API_ENDPOINTS.CONVERSATION_PUBLISH_CHAT_STREAM(conversationId),
        body: { content: content.trim() },
        signal: abortRef.current.signal,
        onEvent: (event) => {
          const data = event.data;

          if (event.event === SSE_EVENT_TYPE.TOOL_RESULT) {
            const tool = data.tool as string | undefined;
            const result = data.result as
              | { project_id?: string; status?: string }
              | undefined;
            if (
              tool === "generate_carousel" &&
              result?.status === "completed"
            ) {
              setCarouselComplete(true);
            }
            return;
          }

          if (event.event === SSE_EVENT_TYPE.TOKEN) {
            const tokenContent = (data.content as string) ?? "";
            streamingContentRef.current += tokenContent;
            setMessages((prev) => {
              const last = prev[prev.length - 1];
              if (
                last?.role === "assistant" &&
                last.id === streamingMsgIdRef.current
              ) {
                return [
                  ...prev.slice(0, -1),
                  { ...last, content: streamingContentRef.current },
                ];
              }
              const newMsg: Message = {
                id: streamingMsgIdRef.current || `stream-${Date.now()}`,
                role: "assistant",
                content: streamingContentRef.current,
                sources: [],
                created_at: new Date().toISOString(),
              };
              if (!streamingMsgIdRef.current) {
                streamingMsgIdRef.current = newMsg.id;
              }
              return [...prev, newMsg];
            });
            return;
          }

          if (event.event === SSE_EVENT_TYPE.COMPLETE) {
            setIsStreaming(false);
            streamingContentRef.current = "";
            streamingMsgIdRef.current = null;
            return;
          }

          if (event.event === SSE_EVENT_TYPE.ERROR) {
            const errorContent = (data.content as string) ?? t("chat.error");
            setIsStreaming(false);
            streamingContentRef.current = "";
            streamingMsgIdRef.current = null;
            setMessages((prev) => [
              ...prev,
              {
                id: `error-${Date.now()}`,
                role: "assistant",
                content: errorContent,
                sources: [],
                created_at: new Date().toISOString(),
              },
            ]);
          }
        },
        onError: () => {
          setIsStreaming(false);
          streamingContentRef.current = "";
          streamingMsgIdRef.current = null;
        },
        onComplete: () => {
          setIsStreaming(false);
        },
      });
    },
    [conversationId, t],
  );

  // Cleanup abort controller on unmount
  useLayoutEffect(() => {
    return () => {
      if (abortRef.current) {
        abortRef.current.abort();
      }
    };
  }, []);

  // Show progress whenever the backend says the project is actively in any
  // phase — not just when this page instance triggered it. A reload mid-run
  // must still render the progress tracker.
  const ACTIVE_PHASES = new Set([
    "pending",
    "researching",
    "drafting",
    "designing",
    "generating_images",
    "exporting",
  ]);
  const currentPhase = statusData?.status || "researching";
  const hasError = statusData?.status === "failed";
  const isGenerating =
    !carouselComplete &&
    !hasError &&
    ACTIVE_PHASES.has(statusData?.status ?? "");

  return (
    <div className="min-h-screen">
      <Header />
      <div className="flex h-[calc(100vh-3.5rem)]" suppressHydrationWarning>
        <div className="flex flex-1 flex-col">
          <div className="border-b border-[var(--color-border)] px-4 py-2">
            <div className="flex items-center justify-between">
              <h2 className="font-medium text-sm">{t("workspace.title")}</h2>
              {carouselComplete && completedProject && (
                <div className="flex items-center gap-2">
                  <Link
                    href={ROUTE_PATHS.BLOG_POST(completedProject.id)}
                    className="rounded-md border border-[var(--color-border)] px-3 py-1 font-medium text-xs transition-colors hover:bg-[var(--color-background)]"
                  >
                    {t("workspace.viewBlog")}
                  </Link>
                  <Link
                    href={ROUTE_PATHS.CREATE_PUBLISH(completedProject.id)}
                    className="rounded-md bg-[var(--color-primary)] px-3 py-1 font-medium text-xs text-[var(--color-text)] transition-colors hover:opacity-90"
                  >
                    {t("workspace.publish")}
                  </Link>
                </div>
              )}
            </div>
          </div>

          <div className="flex-1 overflow-auto p-4">
            <div className="mx-auto max-w-2xl space-y-4">
              {project && (
                <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-background)] p-4">
                  <h3 className="font-medium">{project.topic}</h3>
                  <p className="text-[var(--color-text-muted)] text-sm">
                    {project.audience} · {project.niche}
                  </p>
                </div>
              )}

              {project && (
                <EditorialWorkflowPanel
                  projectId={projectId}
                  topic={project.topic}
                  audience={project.audience}
                  brief={project.niche}
                />
              )}

              <SourceMaterialViewer projectId={projectId} />

              {isGenerating && (
                <CarouselProgress
                  currentPhase={currentPhase}
                  isComplete={false}
                  hasError={false}
                  updatedAt={statusData?.updated_at}
                  errorMessage={statusData?.error_message}
                  phaseProgress={statusData?.phase_progress ?? null}
                />
              )}

              {hasError && (
                <div className="space-y-2">
                  <CarouselProgress
                    currentPhase={currentPhase}
                    isComplete={false}
                    hasError
                    updatedAt={statusData?.updated_at}
                    errorMessage={statusData?.error_message}
                    phaseProgress={statusData?.phase_progress ?? null}
                  />
                  <button
                    type="button"
                    onClick={() =>
                      resumeCarousel.mutate(projectId, {
                        onSuccess: () => stream.reconnect(),
                      })
                    }
                    disabled={resumeCarousel.isPending}
                    className="rounded-md bg-[var(--color-primary)] px-4 py-2 font-medium text-sm text-[var(--color-text)] transition-colors hover:opacity-90 disabled:opacity-50"
                    data-testid="resume-button"
                  >
                    {resumeCarousel.isPending
                      ? t("workspace.resuming")
                      : t("workspace.resume")}
                  </button>
                </div>
              )}

              {isGenerating && !stream.isStreaming && stream.error && (
                <div className="space-y-2">
                  <button
                    type="button"
                    onClick={() => stream.reconnect()}
                    className="rounded-md border border-[var(--color-border)] px-4 py-2 font-medium text-sm transition-colors hover:bg-[var(--color-background)]"
                    data-testid="reconnect-button"
                  >
                    {t("workspace.reconnectStream")}
                  </button>
                </div>
              )}

              {carouselComplete && completedProject && (
                <CarouselPreview project={completedProject} />
              )}

              <MessageList messages={messages} />
            </div>
          </div>

          <div className="border-t border-[var(--color-border)] p-4">
            <div className="mx-auto max-w-2xl">
              <MessageInput
                onSend={handleSendMessage}
                isLoading={isStreaming}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
