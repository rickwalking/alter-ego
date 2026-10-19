"use client";

/**
 * Generation status banner of the blog editor (AE-0425, ADR-0025).
 *
 * In progress: the editor polls and shows how many image slots (cover + one
 * per section) are being generated. Partial: some slots stayed empty (the
 * per-slot image controls live in the section editor, AE-0424). Failed: the
 * draft was kept and the owner retries on the same row; a restart-interrupted
 * run says so. A post from a private carousel warns that it will 404 publicly
 * once published (ADR-0013) and links to the carousel's visibility control.
 */

import Link from "next/link";
import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonSpinner } from "@/components/atoms/neon-spinner";
import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";
import { NEON_AMBER, NEON_CYAN, NEON_RED, TEXT_DIM } from "@/constants/neon";

import {
  ERR_GENERATION_INTERRUPTED,
  GENERATION_STATUS,
  GENERATION_WARNING_CAROUSEL_PRIVATE,
} from "./generation-constants";
import type {
  RetryControlProps,
  BlogGenerationNoticeProps,
  BlogGenerationStatusProps,
  CarouselPrivateWarningProps,
} from "./types";
import { useBlogGeneration } from "./use-blog-generation";

const BANNER_CLASS = "mb-4 rounded-md border px-4 py-3 text-sm";
const NAMESPACE = "dashboard.blogPosts.generation";

/** Retry button; disabled with a "save first" hint while the editor holds
 * unsaved edits (the run would replace them in the editor). */
function RetryControl({
  label,
  retrying,
  retryFailed,
  unsavedChanges,
  onRetry,
}: RetryControlProps): React.ReactElement {
  const t = useTranslations(NAMESPACE);
  return (
    <>
      <NeonButton
        size="sm"
        disabled={retrying || unsavedChanges}
        onClick={onRetry}
      >
        {retrying ? t("retrying") : label}
      </NeonButton>
      {unsavedChanges ? (
        <p className="mt-2" data-testid="retry-save-first">
          {t("saveBeforeRetry")}
        </p>
      ) : null}
      {retryFailed ? <p className="mt-2">{t("retryFailed")}</p> : null}
    </>
  );
}

function FailedNotice({
  state,
  ...retry
}: BlogGenerationNoticeProps): React.ReactElement {
  const t = useTranslations(NAMESPACE);
  const interrupted = state.errors.some(
    (error) => error.code === ERR_GENERATION_INTERRUPTED,
  );
  return (
    <div role="alert" className={BANNER_CLASS} style={{ color: NEON_RED }}>
      <p className="mb-2">{interrupted ? t("interrupted") : t("failed")}</p>
      {state.recoverable ? (
        <RetryControl {...retry} label={t("retry")} />
      ) : null}
    </div>
  );
}

function RunNotice(
  props: BlogGenerationNoticeProps,
): React.ReactElement | null {
  const t = useTranslations(NAMESPACE);
  const { state } = props;
  if (state.status === GENERATION_STATUS.IN_PROGRESS) {
    return (
      <div role="status" className={`${BANNER_CLASS} flex items-center gap-3`}>
        <NeonSpinner />
        <span style={{ color: TEXT_DIM }}>
          {t("inProgress", { slots: state.imageSlots })}
        </span>
      </div>
    );
  }
  if (state.status === GENERATION_STATUS.PARTIAL) {
    // A partial run's retry only fills the empty image slots (never the text).
    return (
      <div role="status" className={BANNER_CLASS} style={{ color: NEON_AMBER }}>
        <p className="mb-2">
          {t("partial", { count: state.imageCount, slots: state.imageSlots })}
        </p>
        <RetryControl
          retrying={props.retrying}
          retryFailed={props.retryFailed}
          unsavedChanges={props.unsavedChanges}
          onRetry={props.onRetry}
          label={t("retryImages")}
        />
      </div>
    );
  }
  if (state.status === GENERATION_STATUS.FAILED) {
    return <FailedNotice {...props} />;
  }
  return null;
}

function CarouselPrivateWarning({
  projectId,
}: CarouselPrivateWarningProps): React.ReactElement {
  const t = useTranslations(NAMESPACE);
  return (
    <p
      role="note"
      data-testid="carousel-private-warning"
      className={BANNER_CLASS}
      style={{ color: NEON_AMBER }}
    >
      {t("carouselPrivate")}{" "}
      {projectId ? (
        <Link
          href={DASHBOARD_ROUTES.CREATE_PUBLISH(projectId)}
          style={{ color: NEON_CYAN }}
        >
          {t("carouselVisibilityLink")}
        </Link>
      ) : null}
    </p>
  );
}

export function BlogGenerationStatus({
  postId,
  unsavedChanges = false,
}: BlogGenerationStatusProps): React.ReactElement | null {
  const { state, projectId, retrying, retryFailed, retry } =
    useBlogGeneration(postId);
  if (!state) {
    return null;
  }
  const isPrivate = state.warnings.includes(
    GENERATION_WARNING_CAROUSEL_PRIVATE,
  );
  return (
    <>
      {isPrivate ? <CarouselPrivateWarning projectId={projectId} /> : null}
      <RunNotice
        state={state}
        retrying={retrying}
        retryFailed={retryFailed}
        unsavedChanges={unsavedChanges}
        onRetry={() => void retry()}
      />
    </>
  );
}
