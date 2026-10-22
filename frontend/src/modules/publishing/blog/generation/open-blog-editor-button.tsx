"use client";

import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { NEON_RED, TEXT_DIM } from "@/constants/neon";

import type { OpenBlogEditorButtonProps } from "./types";
import { useOpenBlogEditor } from "./use-open-blog-editor";

const NOTE_CLASS = "m-0 text-xs";

/** "Abrir no editor do blog": the blog body is edited there, not inline. */
export function OpenBlogEditorButton({
  projectId,
}: Readonly<OpenBlogEditorButtonProps>): React.ReactElement {
  const t = useTranslations("publish.blogEditorLink");
  const { pending, failed, open } = useOpenBlogEditor(projectId);
  return (
    <div className="flex flex-col gap-2">
      <p className={NOTE_CLASS} style={{ color: TEXT_DIM }}>
        {t("body")}
      </p>
      <div>
        <NeonButton size="sm" disabled={pending} onClick={() => void open()}>
          {pending ? t("opening") : t("open")}
        </NeonButton>
      </div>
      {failed ? (
        <p role="alert" className={NOTE_CLASS} style={{ color: NEON_RED }}>
          {t("failed")}
        </p>
      ) : null}
    </div>
  );
}
