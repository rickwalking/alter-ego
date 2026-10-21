"use client";

import { useTranslations } from "next-intl";
import {
  NeonAlert,
  NeonAlertDescription,
} from "@/components/molecules/neon-alert";
import { BLOG_EDITOR_I18N_NAMESPACE } from "@/constants/blog-editor";
import { editorErrorKey } from "../lib/editor-error";
import type { EditorErrorNoticeProps } from "./types";

/**
 * One editor error as a visible, translated alert (AE-0438, F-11).
 *
 * Shared by every editor action surface — the top banner, the review bar, the
 * version sidebar and the per-slot controls — so a failed 422 / 400 / 409 / 5xx
 * is shown next to the control that failed, with the code-specific copy when
 * the backend `detail` is known.
 */
export function EditorErrorNotice({
  error,
}: Readonly<EditorErrorNoticeProps>): React.ReactElement | null {
  const t = useTranslations(BLOG_EDITOR_I18N_NAMESPACE);
  if (!error) {
    return null;
  }
  return (
    <NeonAlert variant="destructive" role="alert">
      <NeonAlertDescription>{t(editorErrorKey(error))}</NeonAlertDescription>
    </NeonAlert>
  );
}
