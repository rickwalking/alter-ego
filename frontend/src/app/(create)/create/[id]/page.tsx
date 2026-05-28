"use client";

import { useCallback, useLayoutEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Header } from "@/components/layout";
import { MessageInput } from "@/features/chat/components";
import { MessageList } from "@/features/chat/components";
import { CarouselPreview } from "@/features/create/components";
import { BriefMaterialsGate } from "@/features/create/components/brief-materials-gate";
import { EditorialWorkflowPanel } from "@/features/create/components/editorial-workflow-panel";
import { SourceMaterialViewer } from "@/features/create/components/source-material-viewer";
import { WorkspaceDraftBlogPreview } from "@/features/create/components/workspace-draft-blog-preview";
import { useCarouselProject } from "@/features/create/hooks";
import { useEditorialWorkflow } from "@/features/create/hooks/use-editorial-workflow";
import { useCreateConversation } from "@/features/chat/hooks/use-chat";
import { streamSseEvents, SSE_EVENT_TYPE } from "@/lib/sse-client";
import { API_ENDPOINTS, ROUTE_PATHS } from "@/constants/api";
import {
  AGENT_ORIGIN_CAROUSEL,
  CONVERSATION_METADATA_AGENT_ORIGIN,
  CONVERSATION_METADATA_PROJECT_ID,
} from "@/constants/publish-chat";
import type { Message } from "@/schemas/chat";
import type { CarouselProjectResponse } from "@/schemas/carousel";
import type { ContentSource } from "@/features/blog/types-ai";

const CONVERSATION_STORAGE_KEY = (projectId: string): string =>
  `alter-ego:conversation:${projectId}`;

export default function WorkspacePage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const t = useTranslations("create");
  const { data: project } = useCarouselProject(projectId);
  const editorialWorkflow = useEditorialWorkflow(projectId);
  const createConversation = useCreateConversation();
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [projectSources, setProjectSources] = useState<ContentSource[]>([]);
  const [workflowStarted, setWorkflowStarted] = useState(false);
  const [publishedProject, setPublishedProject] =
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
        metadata: {
          [CONVERSATION_METADATA_PROJECT_ID]: projectId,
          [CONVERSATION_METADATA_AGENT_ORIGIN]: AGENT_ORIGIN_CAROUSEL,
        },
      })
      .then((conv) => {
        sessionStorage.setItem(CONVERSATION_STORAGE_KEY(projectId), conv.id);
        setConversationId(conv.id);
      })
      .catch(() => {
        // Silently ignore creation errors (e.g. 429 rate-limit).
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

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

  useLayoutEffect(() => {
    return () => {
      if (abortRef.current) {
        abortRef.current.abort();
      }
    };
  }, []);

  const mappedSources = projectSources.map((source) => ({
    title: source.title,
    content: source.content,
    source_type: source.source_type,
  }));

  return (
    <div className="min-h-screen">
      <Header />
      <div className="flex h-[calc(100vh-3.5rem)]" suppressHydrationWarning>
        <div className="flex flex-1 flex-col">
          <div className="border-b border-[var(--color-border)] px-4 py-2">
            <div className="flex items-center justify-between">
              <h2 className="font-medium text-sm">{t("workspace.title")}</h2>
              {publishedProject && (
                <div className="flex items-center gap-2">
                  <Link
                    href={ROUTE_PATHS.BLOG_POST(publishedProject.id)}
                    className="rounded-md border border-[var(--color-border)] px-3 py-1 font-medium text-xs transition-colors hover:bg-[var(--color-background)]"
                  >
                    {t("workspace.viewBlog")}
                  </Link>
                  <Link
                    href={ROUTE_PATHS.CREATE_PUBLISH(publishedProject.id)}
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

              {project && !publishedProject && (
                <WorkspaceDraftBlogPreview projectId={projectId} />
              )}

              <SourceMaterialViewer
                projectId={projectId}
                onSourcesChange={setProjectSources}
              />

              {project &&
                !workflowStarted &&
                !editorialWorkflow.hasActiveWorkflow && (
                  <BriefMaterialsGate
                    sourceCount={projectSources.length}
                    loading={editorialWorkflow.loading}
                    onStartWithMaterials={() => setWorkflowStarted(true)}
                    onStartWithoutMaterials={() => setWorkflowStarted(true)}
                  />
                )}

              {project &&
                (workflowStarted || editorialWorkflow.hasActiveWorkflow) && (
                  <EditorialWorkflowPanel
                    projectId={projectId}
                    topic={project.topic}
                    audience={project.audience}
                    brief={project.niche}
                    sources={mappedSources}
                    autoStart={
                      workflowStarted && !editorialWorkflow.hasActiveWorkflow
                    }
                    onPublished={() => {
                      setPublishedProject(project);
                    }}
                    workflow={editorialWorkflow}
                  />
                )}

              {publishedProject && (
                <CarouselPreview project={publishedProject} />
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
