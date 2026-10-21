"use client";

/**
 * "Create blog post from this carousel" entry point (ADR-0025).
 *
 * Always creates a draft and opens its editor. A carousel that already has a
 * post gets no duplicate: an "already exists" message links to that post. A
 * private carousel is flagged up front: its post would 404 publicly.
 */

import Link from "next/link";
import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";
import { NEON_AMBER, NEON_CYAN, NEON_RED, TEXT_DIM } from "@/constants/neon";

import type { CreateBlogFromCarouselProps } from "./types";
import { useCreateBlogFromCarousel } from "./use-create-blog-from-carousel";

const NOTE_CLASS = "m-0 text-[13px]";

export function CreateBlogFromCarousel({
  projectId,
  isPublic,
}: Readonly<CreateBlogFromCarouselProps>): React.ReactElement {
  const t = useTranslations("publish.blogFromCarousel");
  const { pending, failed, existingPostId, create } =
    useCreateBlogFromCarousel(projectId);
  return (
    <section aria-label={t("title")} className="flex flex-col gap-2">
      <h2 className="m-0 text-sm font-semibold">{t("title")}</h2>
      <p className={NOTE_CLASS} style={{ color: TEXT_DIM }}>
        {t("body")}
      </p>
      {isPublic ? null : (
        <p
          role="note"
          data-testid="carousel-private-warning"
          className={NOTE_CLASS}
          style={{ color: NEON_AMBER }}
        >
          {t("privateWarning")}
        </p>
      )}
      <div>
        <NeonButton size="sm" disabled={pending} onClick={() => void create()}>
          {pending ? t("creating") : t("create")}
        </NeonButton>
      </div>
      {existingPostId ? (
        <p role="status" className={NOTE_CLASS}>
          {t("exists")}{" "}
          <Link
            href={DASHBOARD_ROUTES.BLOG_POST_EDIT(existingPostId)}
            style={{ color: NEON_CYAN }}
          >
            {t("openExisting")}
          </Link>
        </p>
      ) : null}
      {failed ? (
        <p role="alert" className={NOTE_CLASS} style={{ color: NEON_RED }}>
          {t("failed")}
        </p>
      ) : null}
    </section>
  );
}
