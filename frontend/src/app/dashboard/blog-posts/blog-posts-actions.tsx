"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonModal } from "@/components/molecules/neon-modal";
import { BLOG_POSTS_I18N_NAMESPACE } from "@/modules/editorial-operations";
import { BLOG_POST_ORIGIN_CAROUSEL } from "@/modules/publishing";
import { ROUTE_PATHS } from "@/constants/api";
import type {
  BlogPostCardActionsProps,
  DeleteConfirmModalProps,
} from "@/app/dashboard/blog-posts/types";

const PUBLISHED_STATUS = "published";

/**
 * Edit / Hide / Delete controls per card (AE-0296). Hide is offered for
 * published posts (unpublish → draft; restore = normal publish workflow).
 * Delete is hidden for carousel-origin posts — the backend 409-guards them
 * while linked to their project; Hide (or deleting the carousel) is the path.
 */
export function BlogPostCardActions({
  post,
  actions,
}: BlogPostCardActionsProps): React.ReactElement {
  const t = useTranslations(BLOG_POSTS_I18N_NAMESPACE);
  const deletable = post.origin !== BLOG_POST_ORIGIN_CAROUSEL;
  return (
    <div className="flex flex-wrap gap-2 mt-3">
      <Link href={ROUTE_PATHS.BLOG_POST_EDIT(post.id)}>
        <NeonButton size="sm" variant="outline">
          {t("actions.edit")}
        </NeonButton>
      </Link>
      {post.status === PUBLISHED_STATUS && (
        <NeonButton
          size="sm"
          variant="ghost"
          onClick={() => actions.onHide(post)}
        >
          {t("actions.hide")}
        </NeonButton>
      )}
      {deletable && (
        <NeonButton
          size="sm"
          variant="ghost"
          className="text-neon-red"
          onClick={() => actions.onDelete(post)}
        >
          {t("actions.delete")}
        </NeonButton>
      )}
    </div>
  );
}

export function DeleteConfirmModal({
  post,
  onConfirm,
  onCancel,
}: DeleteConfirmModalProps): React.ReactElement | null {
  const t = useTranslations(BLOG_POSTS_I18N_NAMESPACE);
  if (!post) {
    return null;
  }
  return (
    <NeonModal
      open
      onClose={onCancel}
      title={t("actions.delete")}
      footer={
        <>
          <NeonButton variant="outline" size="sm" onClick={onCancel}>
            {t("actions.cancel")}
          </NeonButton>
          <NeonButton variant="danger" size="sm" onClick={onConfirm}>
            {t("actions.delete")}
          </NeonButton>
        </>
      }
    >
      <p className="text-sm text-text-primary">{t("confirmDelete")}</p>
      <p className="mt-2 text-xs text-text-muted">{post.title}</p>
    </NeonModal>
  );
}
