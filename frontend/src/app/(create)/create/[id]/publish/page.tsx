"use client";

import { useState, useCallback, useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Header } from "@/components/layout";
import { MessageInput, MessageList } from "@/features/chat/components";
import { useCarouselProject } from "@/features/create/hooks";
import { useEditorialWorkflow } from "@/features/create/hooks/use-editorial-workflow";
import { PublishPanel } from "@/features/publish/components";
import { usePublishInstagram, usePublishChat } from "@/features/publish/hooks";
import { ROUTE_PATHS, API_ENDPOINTS, HTTP_METHODS } from "@/constants/api";
import { EDITORIAL_WORKFLOW_STATUS } from "@/constants/editorial-workflow";
import { authenticatedFetch } from "@/lib/authenticated-fetch";

type PublishResult = {
  status: "idle" | "success" | "error";
  message?: string;
};

export default function PublishPage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const t = useTranslations("publish");
  const { data: project, isLoading } = useCarouselProject(projectId);
  const workflow = useEditorialWorkflow(projectId);
  const publishInstagram = usePublishInstagram();
  const { messages, isStreaming, sendMessage } = usePublishChat(projectId);
  const [publishResult, setPublishResult] = useState<PublishResult>({
    status: "idle",
  });
  const [sitePublishMessage, setSitePublishMessage] = useState<string | null>(
    null,
  );

  useEffect(() => {
    void workflow.refreshState();
  }, [workflow.refreshState]);

  const canPublishToSite =
    workflow.state?.workflow_status ===
    EDITORIAL_WORKFLOW_STATUS.APPROVED_FOR_PUBLISH;

  const handlePublishToSite = useCallback(async (): Promise<void> => {
    setSitePublishMessage(null);
    try {
      const response = await authenticatedFetch(
        API_ENDPOINTS.CAROUSEL_PUBLISH(projectId),
        { method: HTTP_METHODS.POST },
      );
      if (!response.ok) {
        throw new Error(await response.text());
      }
      setSitePublishMessage(t("sitePublished"));
      await workflow.refreshState();
    } catch (error) {
      setSitePublishMessage(
        error instanceof Error ? error.message : t("sitePublishFailed"),
      );
    }
  }, [projectId, t, workflow.refreshState]);

  const handlePublishInstagram = useCallback(
    async (caption: string) => {
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
    },
    [projectId, publishInstagram, t],
  );

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
        <p className="p-8 text-destructive">{t("notFound")}</p>
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
        {!canPublishToSite && (
          <p className="mb-4 rounded-md border border-[var(--color-border)] p-3 text-[var(--color-text-muted)] text-sm">
            {t("awaitingFinalApproval")}
          </p>
        )}
        {canPublishToSite && (
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <button
              type="button"
              className="rounded-md bg-[var(--color-primary)] px-4 py-2 text-sm text-white"
              onClick={() => void handlePublishToSite()}
            >
              {t("publishToSite")}
            </button>
            {sitePublishMessage ? (
              <span className="text-[var(--color-text-muted)] text-sm">
                {sitePublishMessage}
              </span>
            ) : null}
          </div>
        )}
        <PublishPanel
          project={project}
          onPublishInstagram={
            canPublishToSite ? handlePublishInstagram : undefined
          }
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
            <MessageInput onSend={sendMessage} isLoading={isStreaming} />
          </div>
        </section>
      </main>
    </div>
  );
}
