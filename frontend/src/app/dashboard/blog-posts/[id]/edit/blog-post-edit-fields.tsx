"use client";

import { useTranslations } from "next-intl";
import { NeonInput } from "@/components/atoms/neon-input";
import { NeonTextarea } from "@/components/atoms/neon-textarea";
import {
  BLOG_EXCERPT_MAX_LENGTH,
  BLOG_TITLE_MAX_LENGTH,
} from "@/modules/publishing";
import { BLOG_POSTS_I18N_NAMESPACE } from "@/modules/editorial-operations";
import { NEON_RED } from "@/constants/neon";
import type {
  BlogPostEditFieldsProps,
  FieldErrorProps,
} from "@/app/dashboard/blog-posts/types";

const TITLE_ID = "blog-post-title";
const TITLE_ERROR_ID = "blog-post-title-error";
const EXCERPT_ID = "blog-post-excerpt";
const EXCERPT_ERROR_ID = "blog-post-excerpt-error";
const LABEL_CLASS = "mb-1 block text-xs font-semibold text-text-muted";
const EXCERPT_ROWS = 2;

function FieldError({
  id,
  message,
}: Readonly<FieldErrorProps>): React.ReactElement | null {
  if (!message) {
    return null;
  }
  return (
    <p
      id={id}
      role="alert"
      className="mt-1 text-xs"
      style={{ color: NEON_RED }}
    >
      {message}
    </p>
  );
}

/**
 * Title / excerpt fields of the blog editor (AE-0411, B19): labelled,
 * `required` + `maxLength` matching the backend limits, with inline errors.
 * The body is edited per section by the `blog.v2` section editor (AE-0424).
 */
export function BlogPostEditFields({
  title,
  onTitleChange,
  excerpt,
  onExcerptChange,
  validation,
}: Readonly<BlogPostEditFieldsProps>): React.ReactElement {
  const t = useTranslations(BLOG_POSTS_I18N_NAMESPACE);
  const titleError = validation.title
    ? t(`validation.${validation.title}`, { max: BLOG_TITLE_MAX_LENGTH })
    : null;
  const excerptError = validation.excerpt
    ? t(`validation.${validation.excerpt}`, { max: BLOG_EXCERPT_MAX_LENGTH })
    : null;
  return (
    <>
      <div>
        <label htmlFor={TITLE_ID} className={LABEL_CLASS}>
          {t("fields.title")}
        </label>
        <NeonInput
          id={TITLE_ID}
          value={title}
          required
          maxLength={BLOG_TITLE_MAX_LENGTH}
          aria-invalid={titleError ? true : undefined}
          aria-describedby={titleError ? TITLE_ERROR_ID : undefined}
          onChange={(e) => onTitleChange(e.target.value)}
        />
        <FieldError id={TITLE_ERROR_ID} message={titleError} />
      </div>
      <div>
        <label htmlFor={EXCERPT_ID} className={LABEL_CLASS}>
          {t("fields.excerpt")}
        </label>
        <NeonTextarea
          id={EXCERPT_ID}
          value={excerpt}
          rows={EXCERPT_ROWS}
          maxLength={BLOG_EXCERPT_MAX_LENGTH}
          aria-invalid={excerptError ? true : undefined}
          aria-describedby={excerptError ? EXCERPT_ERROR_ID : undefined}
          onChange={(e) => onExcerptChange(e.target.value)}
        />
        <FieldError id={EXCERPT_ERROR_ID} message={excerptError} />
      </div>
    </>
  );
}
