"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslations } from "next-intl";
import { Header } from "@/components/layout";
import { MessageInput, MessageList } from "@/features/chat/components";
import { useCreateConversation } from "@/features/chat/hooks/use-chat";
import { useCarouselProject } from "@/features/create/hooks";
import { PublishPanel } from "@/features/publish/components";
import { usePublishInstagram } from "@/features/publish/hooks";
import { ROUTE_PATHS } from "@/constants/api";
import type { Message } from "@/schemas/chat";

const WS_TOKEN_TYPE = "token";
const WS_COMPLETE_TYPE = "complete";
const WS_ERROR_TYPE = "error";
const WS_TOOL_RESULT_TYPE = "tool_result";

type PublishResult = {
  status: "idle" | "success" | "error";
  message?: string;
};

// Module-level guard: persists across React Strict Mode double-mounts
// and HMR remounts so we only create one conversation per project.
const _publishConversationsInitiated = new Set<string>();

export default function PublishPage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const t = useTranslations("publish");
  const { data: project, isLoading } = useCarouselProject(projectId);
  const publishInstagram = usePublishInstagram();
  const queryClient = useQueryClient();
  const createConversation = useCreateConversation();
  const [publishResult, setPublishResult] = useState<PublishResult>({
    status: "idle",
  });
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const streamingContentRef = useRef("");
  const streamingMsgIdRef = useRef<string | null>(null);

  // Seed a conversation once, so the chat drawer is wired to the existing
  // WebSocket chat pipeline. The refine_carousel_copy tool lives on the
  // RAG agent — the user says "shorten the LinkedIn post" in plain text
  // and the agent picks the right target.
  useEffect(() => {
    if (!projectId || conversationId || _publishConversationsInitiated.has(projectId)) {
      return;
    }
    _publishConversationsInitiated.add(projectId);
    void createConversation
      .mutateAsync({ title: `Refine: ${projectId}` })
      .then((conv) => setConversationId(conv.id));

    return () => {
      _publishConversationsInitiated.delete(projectId);
    };
  }, [projectId, conversationId, createConversation]);

  useEffect(() => {
    if (!conversationId) return;
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const socket = new WebSocket(
      `${protocol}//${window.location.host}/ws/chat/${conversationId}`,
    );

    socket.onclose = () => setIsStreaming(false);

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as Record<string, unknown>;

        if (data.type === WS_TOOL_RESULT_TYPE) {
          const toolResult = data as { tool?: string };
          if (toolResult.tool === "refine_carousel_copy") {
            queryClient.invalidateQueries({
              queryKey: ["carousel", projectId],
            });
          }
          return;
        }

        if (data.type === WS_TOKEN_TYPE) {
          const tokenData = data as { content?: string };
          streamingContentRef.current += tokenData.content ?? "";
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

        if (data.type === WS_COMPLETE_TYPE) {
          setIsStreaming(false);
          streamingContentRef.current = "";
          streamingMsgIdRef.current = null;
          return;
        }

        if (data.type === WS_ERROR_TYPE) {
          setIsStreaming(false);
          streamingContentRef.current = "";
          streamingMsgIdRef.current = null;
        }
      } catch {
        // Ignore parse errors.
      }
    };

    wsRef.current = socket;
    return () => {
      socket.close();
      wsRef.current = null;
    };
  }, [conversationId, projectId, queryClient]);

  const handleSendMessage = useCallback(
    (content: string) => {
      if (!content.trim() || wsRef.current?.readyState !== WebSocket.OPEN) {
        return;
      }
      const userMsg: Message = {
        id: `user-${Date.now()}`,
        role: "user",
        content: content.trim(),
        sources: [],
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);
      // Prefix the project id into the message so the agent knows which
      // project to refine. Users can still be terse ("shorten LI post").
      const contextPrefix = `(carousel project_id=${projectId}) `;
      wsRef.current.send(
        JSON.stringify({ content: contextPrefix + content.trim() }),
      );
      setIsStreaming(true);
      streamingMsgIdRef.current = null;
      streamingContentRef.current = "";
    },
    [projectId],
  );

  const handlePublishInstagram = async (caption: string) => {
    try {
      const result = await publishInstagram.mutateAsync({
        projectId,
        caption,
      });
      if (result.status === "failed") {
        setPublishResult({
          status: "error",
          message: result.error_message ?? t("instagram.failed"),
        });
        return;
      }
      setPublishResult({
        status: "success",
        message:
          result.status === "published"
            ? t("instagram.published")
            : t("instagram.queued"),
      });
    } catch (error) {
      setPublishResult({
        status: "error",
        message:
          error instanceof Error ? error.message : t("instagram.failed"),
      });
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen">
        <Header />
        <p className="p-8 text-[var(--color-text-muted)]">{t("loading")}</p>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="min-h-screen">
        <Header />
        <p className="p-8 text-red-500">{t("notFound")}</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <Header />
      <div className="border-b border-[var(--color-border)] px-4 py-3">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <div>
            <h1 className="font-semibold text-lg">
              {project.title || project.topic}
            </h1>
            <p className="text-[var(--color-text-muted)] text-sm">
              {project.audience} · {project.niche}
            </p>
          </div>
          <Link
            href={ROUTE_PATHS.CREATE_WORKSPACE(projectId)}
            className="text-sm hover:underline"
          >
            {t("backToWorkspace")}
          </Link>
        </div>
      </div>
      <main className="mx-auto max-w-6xl p-4">
        <PublishPanel
          project={project}
          onPublishInstagram={handlePublishInstagram}
          isPublishingInstagram={publishInstagram.isPending}
          publishResult={publishResult}
        />
        <section
          aria-label={t("chatLabel")}
          className="mt-8 rounded-lg border border-[var(--color-border)]"
        >
          <header className="border-b border-[var(--color-border)] px-4 py-2">
            <h2 className="font-medium text-sm">{t("chatTitle")}</h2>
            <p className="text-[var(--color-text-muted)] text-xs">
              {t("chatHelp")}
            </p>
          </header>
          <div className="max-h-96 overflow-auto p-4">
            <MessageList messages={messages} />
          </div>
          <div className="border-t border-[var(--color-border)] p-3">
            <MessageInput onSend={handleSendMessage} isLoading={isStreaming} />
          </div>
        </section>
      </main>
    </div>
  );
}
