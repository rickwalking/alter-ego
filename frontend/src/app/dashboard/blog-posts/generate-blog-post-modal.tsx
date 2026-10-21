"use client";

import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonInput } from "@/components/atoms/neon-input";
import { NeonModal } from "@/components/molecules/neon-modal";
import { NEON_RED, TEXT_DIM } from "@/constants/neon";
import { GENERATION_TOPIC_MAX_CHARS } from "@/modules/publishing";
import { useGenerateBlogPost } from "@/app/dashboard/blog-posts/use-generate-blog-post";

const NAMESPACE = "dashboard.blogPosts.generation";
const TOPIC_INPUT_ID = "generate-blog-topic";

/** "Generate with AI" button + topic modal of the Blog Posts top bar. */
export function GenerateBlogPostAction(): React.ReactElement {
  const t = useTranslations(NAMESPACE);
  const generate = useGenerateBlogPost();
  return (
    <>
      <NeonButton size="sm" variant="outline" onClick={generate.show}>
        {t("generateWithAi")}
      </NeonButton>
      <NeonModal
        open={generate.open}
        onClose={generate.hide}
        title={t("modalTitle")}
        footer={
          <>
            <NeonButton size="sm" variant="outline" onClick={generate.hide}>
              {t("cancel")}
            </NeonButton>
            <NeonButton
              size="sm"
              disabled={!generate.canSubmit}
              onClick={() => void generate.submit()}
            >
              {generate.pending ? t("starting") : t("submit")}
            </NeonButton>
          </>
        }
      >
        <label htmlFor={TOPIC_INPUT_ID} className="mb-1 block text-sm">
          {t("topicLabel")}
        </label>
        <NeonInput
          id={TOPIC_INPUT_ID}
          value={generate.topic}
          maxLength={GENERATION_TOPIC_MAX_CHARS}
          placeholder={t("topicPlaceholder")}
          onChange={(event) => generate.setTopic(event.target.value)}
        />
        <p className="mt-2 text-[13px]" style={{ color: TEXT_DIM }}>
          {t("topicHint")}
        </p>
        {generate.failed ? (
          <p
            role="alert"
            className="mt-2 text-[13px]"
            style={{ color: NEON_RED }}
          >
            {t("startFailed")}
          </p>
        ) : null}
      </NeonModal>
    </>
  );
}
