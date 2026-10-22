"use client";

import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonInput } from "@/components/atoms/neon-input";
import { NeonModal } from "@/components/molecules/neon-modal";
import { NEON_RED } from "@/constants/neon";
import { BLOG_POSTS_I18N_NAMESPACE } from "@/modules/editorial-operations";
import type { useBlogPosts } from "@/modules/publishing";
import { useNewBlogPost } from "./use-new-blog-post";

const TITLE_INPUT_ID = "new-blog-post-title";
const BLOG_POST_TITLE_MAX_CHARS = 255;

/** "New Post" button + title form; the draft is created only on submit. */
export function NewBlogPostAction({
  create,
}: Readonly<{
  create: ReturnType<typeof useBlogPosts>["create"];
}>): React.ReactElement {
  const t = useTranslations(BLOG_POSTS_I18N_NAMESPACE);
  const form = useNewBlogPost(create);
  return (
    <>
      <NeonButton
        size="sm"
        onClick={form.show}
        icon={
          <svg
            width="14"
            height="14"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path d="M12 5v14" strokeLinecap="round" />
            <path d="M5 12h14" strokeLinecap="round" />
          </svg>
        }
      >
        {t("newPost")}
      </NeonButton>
      <NeonModal
        open={form.open}
        onClose={form.hide}
        title={t("createNew")}
        footer={
          <>
            <NeonButton size="sm" variant="outline" onClick={form.hide}>
              {t("actions.cancel")}
            </NeonButton>
            <NeonButton
              size="sm"
              disabled={!form.canSubmit}
              onClick={() => void form.submit()}
            >
              {t("actions.create")}
            </NeonButton>
          </>
        }
      >
        <label htmlFor={TITLE_INPUT_ID} className="mb-1 block text-sm">
          {t("fields.title")}
        </label>
        <NeonInput
          id={TITLE_INPUT_ID}
          value={form.title}
          maxLength={BLOG_POST_TITLE_MAX_CHARS}
          required
          onChange={(event) => form.setTitle(event.target.value)}
        />
        {form.createError ? (
          <p
            role="alert"
            className="mt-2 text-[13px]"
            style={{ color: NEON_RED }}
          >
            {form.createError}
          </p>
        ) : null}
      </NeonModal>
    </>
  );
}
