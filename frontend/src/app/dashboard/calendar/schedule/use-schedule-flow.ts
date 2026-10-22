"use client";

import { useCallback, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import type { BlogPost } from "@/modules/publishing";
import { formatLocaleDateTime } from "@/lib/locale-format";
import type { UseScheduleFlowResult } from "./types";

/**
 * Open/close state of the Schedule Post dialog on the calendar page. A
 * successful schedule closes it, re-fetches the calendar so the post shows on
 * its new date and leaves a notice naming the post and its local time.
 */
export function useScheduleFlow(
  refetch: () => Promise<void>,
): UseScheduleFlowResult {
  const t = useTranslations("workflow.calendar");
  const locale = useLocale();
  const [open, setOpen] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const openDialog = useCallback(() => {
    setNotice(null);
    setOpen(true);
  }, []);
  const close = useCallback(() => setOpen(false), []);
  const onScheduled = useCallback(
    (post: BlogPost) => {
      setOpen(false);
      setNotice(
        t("scheduledNotice", {
          title: post.title,
          date: formatLocaleDateTime(post.scheduled_publish_at, locale),
        }),
      );
      void refetch();
    },
    [t, locale, refetch],
  );

  return { open, notice, openDialog, close, onScheduled };
}
