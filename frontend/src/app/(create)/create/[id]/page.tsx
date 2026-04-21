"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Header } from "@/components/layout";
import { MessageInput } from "@/features/chat/components";
import { MessageList } from "@/features/chat/components";
import { CarouselProgress, CarouselPreview } from "@/features/create/components";
import {
  useCarouselProject,
  useCarouselStatus,
  useGenerateCarousel,
} from "@/features/create/hooks";
import { useCreateConversation } from "@/features/chat/hooks/use-chat";
import { ROUTE_PATHS } from "@/constants/api";
import type { Message } from "@/schemas/chat";
import type { CarouselProjectResponse } from "@/schemas/carousel";

const WS_TOKEN_TYPE = "token";
const WS_COMPLETE_TYPE = "complete";
const WS_ERROR_TYPE = "error";
const WS_TOOL_RESULT_TYPE = "tool_result";

export default function WorkspacePage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const t = useTranslations("create");
  const { data: project } = useCarouselProject(projectId);
  const { data: statusData } = useCarouselStatus(projectId);
  const generateCarousel = useGenerateCarousel();
  const createConversation = useCreateConversation();
  const generationTriggeredRef = useRef(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [carouselComplete, setCarouselComplete] = useState(false);
  const [completedProject, setCompletedProject] = useState<CarouselProjectResponse | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const streamingContentRef = useRef("");
  const streamingMsgIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (!projectId) return;

    const setupConversation = async () => {
      const conv = await createConversation.mutateAsync({
        title: `Carousel: ${project?.topic || projectId}`,
      });
      setConversationId(conv.id);
    };

    setupConversation();
  }, [projectId]);

  useEffect(() => {
    if (!conversationId) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/chat/${conversationId}`;
    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      // Connection established
    };

    socket.onclose = () => {
      setIsStreaming(false);
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as Record<string, unknown>;

        if (data.type === WS_TOOL_RESULT_TYPE) {
          const toolResult = data as { tool?: string; result?: { project_id?: string; status?: string } };
          if (toolResult.tool === "generate_carousel" && toolResult.result?.status === "completed") {
            setCarouselComplete(true);
          }
          return;
        }

        if (data.type === WS_TOKEN_TYPE) {
          const tokenData = data as { content?: string };
          streamingContentRef.current += tokenData.content || "";
          setMessages((prev) => {
            const last = prev[prev.length - 1];
            if (last?.role === "assistant" && last.id === streamingMsgIdRef.current) {
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

        if (data.type === WS_COMPLETE_TYPE) {
          setIsStreaming(false);
          streamingContentRef.current = "";
          streamingMsgIdRef.current = null;
          return;
        }

        if (data.type === WS_ERROR_TYPE) {
          const errorData = data as { content?: string };
          setIsStreaming(false);
          streamingContentRef.current = "";
          streamingMsgIdRef.current = null;
          setMessages((prev) => [
            ...prev,
            {
              id: `error-${Date.now()}`,
              role: "assistant",
              content: errorData.content || t("chat.error"),
              sources: [],
              created_at: new Date().toISOString(),
            },
          ]);
        }
      } catch {
        // Ignore parse errors
      }
    };

    wsRef.current = socket;

    return () => {
      socket.close();
      wsRef.current = null;
    };
  }, [conversationId, t]);

  useEffect(() => {
    if (statusData?.status === "completed" && project) {
      setCarouselComplete(true);
      setCompletedProject(project);
    }
  }, [statusData?.status, project]);

  // Auto-trigger the pipeline once per project when we see it in `pending`.
  // The ref prevents a second fire if the status query refetches before the
  // backend has transitioned out of pending.
  useEffect(() => {
    if (
      !projectId ||
      generationTriggeredRef.current ||
      generateCarousel.isPending ||
      statusData?.status !== "pending"
    ) {
      return;
    }
    generationTriggeredRef.current = true;
    generateCarousel.mutate({ projectId });
  }, [projectId, statusData?.status, generateCarousel]);

  const handleSendMessage = useCallback((content: string) => {
    if (!content.trim()) return;

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      role: "user",
      content: content.trim(),
      sources: [],
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ content: content.trim() }));
      setIsStreaming(true);
      streamingMsgIdRef.current = null;
      streamingContentRef.current = "";
    }
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
    !carouselComplete && !hasError && ACTIVE_PHASES.has(statusData?.status ?? "");

  return (
    <div className="min-h-screen">
      <Header />
      <div className="flex h-[calc(100vh-3.5rem)]" suppressHydrationWarning>
        <div className="flex flex-1 flex-col">
          <div className="border-b border-[var(--color-border)] px-4 py-2">
            <div className="flex items-center justify-between">
              <h2 className="font-medium text-sm">{t("workspace.title")}</h2>
              {carouselComplete && completedProject && (
                <Link
                  href={ROUTE_PATHS.BLOG_POST(completedProject.id)}
                  className="rounded-md bg-[var(--color-primary)] px-3 py-1 font-medium text-xs text-[var(--color-text)] transition-colors hover:opacity-90"
                >
                  {t("workspace.viewBlog")}
                </Link>
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

              {isGenerating && (
                <CarouselProgress
                  currentPhase={currentPhase}
                  isComplete={false}
                  hasError={false}
                  updatedAt={statusData?.updated_at}
                  errorMessage={statusData?.error_message}
                />
              )}

              {hasError && (
                <CarouselProgress
                  currentPhase={currentPhase}
                  isComplete={false}
                  hasError
                  updatedAt={statusData?.updated_at}
                  errorMessage={statusData?.error_message}
                />
              )}

              {carouselComplete && completedProject && (
                <CarouselPreview project={completedProject} />
              )}

              <MessageList messages={messages} />
            </div>
          </div>

          <div className="border-t border-[var(--color-border)] p-4">
            <div className="mx-auto max-w-2xl">
              <MessageInput onSend={handleSendMessage} isLoading={isStreaming} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
