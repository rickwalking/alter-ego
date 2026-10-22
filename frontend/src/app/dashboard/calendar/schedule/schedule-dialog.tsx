"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonSpinner } from "@/components/atoms/neon-spinner";
import { NeonAlert } from "@/components/molecules/neon-alert";
import { NeonModal } from "@/components/molecules/neon-modal";
import { ROUTE_PATHS } from "@/constants/api";
import { ScheduleForm } from "./schedule-form";
import { useScheduleDialog } from "./use-schedule-dialog";
import type { ScheduleDialogBodyProps, ScheduleDialogProps } from "./types";

function ScheduleDialogBody({
  state,
}: Readonly<ScheduleDialogBodyProps>): React.ReactElement {
  const t = useTranslations("workflow.calendar.schedule");
  if (state.loading) {
    return <NeonSpinner size="md" />;
  }
  if (state.loadError) {
    return <NeonAlert variant="destructive">{t("loadFailed")}</NeonAlert>;
  }
  if (state.posts.length === 0 && state.unapproved.length === 0) {
    return (
      <p className="text-sm">
        {t("empty")}{" "}
        <Link href={ROUTE_PATHS.BLOG_POSTS} className="underline">
          {t("openBlogPosts")}
        </Link>
      </p>
    );
  }
  return (
    <ScheduleForm
      posts={state.posts}
      unapproved={state.unapproved}
      draft={state.draft}
      onDraftChange={state.setDraft}
      minTime={state.minTime}
      conflicts={state.conflicts}
    />
  );
}

function ScheduleDialogContent({
  onClose,
  onScheduled,
}: Readonly<Omit<ScheduleDialogProps, "open">>): React.ReactElement {
  const t = useTranslations("workflow.calendar.schedule");
  const state = useScheduleDialog(onScheduled);
  const footer = (
    <div className="mt-6 flex justify-end gap-2">
      <NeonButton variant="ghost" onClick={onClose}>
        {t("cancel")}
      </NeonButton>
      <NeonButton
        loading={state.submitting}
        disabled={state.submitting || state.posts.length === 0}
        onClick={() => void state.submit()}
      >
        {state.submitting ? t("submitting") : t("submit")}
      </NeonButton>
    </div>
  );
  return (
    <NeonModal open onClose={onClose} title={t("title")} footer={footer}>
      <p className="mb-4 text-xs opacity-70">{t("hint")}</p>
      <ScheduleDialogBody state={state} />
      {state.error && (
        <NeonAlert variant="destructive" className="mt-4">
          {t(`errors.${state.error}`)}
        </NeonAlert>
      )}
    </NeonModal>
  );
}

/**
 * Schedule Post: pick an approved blog post and a future local time; the due
 * post sweep publishes it then. Mounted only while open, so the approved posts
 * load when it opens and the form starts empty each time.
 */
export function ScheduleDialog({
  open,
  onClose,
  onScheduled,
}: Readonly<ScheduleDialogProps>): React.ReactElement | null {
  return open ? (
    <ScheduleDialogContent onClose={onClose} onScheduled={onScheduled} />
  ) : null;
}
