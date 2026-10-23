"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonConfirmDialog } from "@/components/molecules/neon-confirm-dialog";
import { NEON_RED, TEXT_DIM } from "@/constants/neon";

import type { OpenBlogEditorButtonProps } from "./types";
import { useOpenBlogEditor } from "./use-open-blog-editor";

const NOTE_CLASS = "m-0 text-xs";

/**
 * "Abrir no editor do blog": the blog body is edited there, not inline. The
 * click asks first, because a carousel without a post gets its draft generated
 * by the blog writer (an LLM run). While the page has unsaved edits the button
 * waits (the navigation would drop them).
 */
export function OpenBlogEditorButton({
  projectId,
  blocked = false,
}: Readonly<OpenBlogEditorButtonProps>): React.ReactElement {
  const t = useTranslations("publish.blogEditorLink");
  const { pending, failed, open } = useOpenBlogEditor(projectId);
  const [asking, setAsking] = useState(false);
  return (
    <div className="flex flex-col gap-2">
      <p className={NOTE_CLASS} style={{ color: TEXT_DIM }}>
        {t("body")}
      </p>
      <div>
        <NeonButton
          size="sm"
          disabled={pending || blocked}
          onClick={() => setAsking(true)}
        >
          {pending ? t("opening") : t("open")}
        </NeonButton>
      </div>
      {blocked ? (
        <p className={NOTE_CLASS} style={{ color: TEXT_DIM }}>
          {t("blocked")}
        </p>
      ) : null}
      {failed ? (
        <p role="alert" className={NOTE_CLASS} style={{ color: NEON_RED }}>
          {t("failed")}
        </p>
      ) : null}
      {asking ? (
        <NeonConfirmDialog
          title={t("confirm.title")}
          body={t("confirm.body")}
          confirmLabel={t("confirm.confirm")}
          cancelLabel={t("confirm.cancel")}
          errorFallback={t("failed")}
          onConfirm={async () => {
            setAsking(false);
            await open();
          }}
          onClose={() => setAsking(false)}
        />
      ) : null}
    </div>
  );
}
