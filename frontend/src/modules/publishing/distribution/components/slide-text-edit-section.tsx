"use client";

import { useCallback, useState } from "react";
import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { TEXT_DIM } from "@/constants/neon";
import {
  applySlideCopyEdit,
  applySlideStructuredItemEdit,
  SlideCopyEditor,
  slidesHaveCopyChanges,
  type SlideCopyEdit,
  type SlideStructuredItemEdit,
} from "@/modules/editorial";
import { SECTION_CARD_STYLE } from "@/modules/publishing/distribution/constants";
import { useEditCarouselSlides } from "@/modules/publishing/distribution/hooks/use-edit-carousel-slides";
import { useRepublishCarousel } from "@/modules/publishing/distribution/hooks/use-republish-carousel";
import type { LocalizedSlideReview } from "@/modules/publishing/blog/types-ai";
import type { SlideTextEditSectionProps } from "./types";

function RunInProgressCard(): React.ReactElement {
  const t = useTranslations("publish.slideEditor");
  return (
    <div style={SECTION_CARD_STYLE}>
      <h3 className="text-sm font-semibold mb-1">{t("title")}</h3>
      <p className="text-xs" style={{ color: TEXT_DIM }} role="status">
        {t("blockedRunInProgress")}
      </p>
    </div>
  );
}

export function SlideTextEditSection(
  props: SlideTextEditSectionProps,
): React.ReactElement {
  const { projectId, slides, policyVersion, runInProgress, onEdited } = props;
  const t = useTranslations("publish.slideEditor");
  const editMutation = useEditCarouselSlides();
  const republish = useRepublishCarousel();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<LocalizedSlideReview[]>(slides);
  const [blocked, setBlocked] = useState(false);
  const [done, setDone] = useState(false);

  const open = useCallback(() => {
    setDraft(slides);
    setBlocked(false);
    setDone(false);
    setEditing(true);
  }, [slides]);

  const onCopyChange = useCallback((edit: SlideCopyEdit) => {
    setDraft((current) => applySlideCopyEdit(current, edit));
  }, []);

  const onStructuredItemChange = useCallback(
    (edit: SlideStructuredItemEdit) => {
      setDraft((current) => applySlideStructuredItemEdit(current, edit));
    },
    [],
  );

  const save = useCallback(() => {
    setBlocked(false);
    editMutation.mutate(
      { projectId, editedSlides: draft },
      {
        onSuccess: (data) => {
          if (data.validation.blocking === true) {
            setBlocked(true);
            return;
          }
          setEditing(false);
          setDone(true);
          republish.mutate({ projectId }, { onSuccess: () => onEdited() });
        },
      },
    );
  }, [projectId, draft, editMutation, republish, onEdited]);

  if (runInProgress) {
    return <RunInProgressCard />;
  }

  const pending = republish.isPending || props.rebuildPending === true;
  const dirty = slidesHaveCopyChanges(slides, draft);

  return (
    <div style={SECTION_CARD_STYLE}>
      <h3 className="text-sm font-semibold mb-1">{t("title")}</h3>
      <p className="text-xs mb-2" style={{ color: TEXT_DIM }}>
        {t("noImageRegen")}
      </p>
      {!editing ? (
        <NeonButton size="sm" onClick={open}>
          {t("editText")}
        </NeonButton>
      ) : (
        <div className="space-y-3">
          <SlideCopyEditor
            slides={draft}
            idPrefix="publish-edit"
            policyVersion={policyVersion}
            showBudget
            onCopyChange={onCopyChange}
            onStructuredItemChange={onStructuredItemChange}
          />
          {blocked ? (
            <p className="text-destructive text-xs" role="alert">
              {t("blockingViolations")}
            </p>
          ) : null}
          <div className="flex flex-wrap items-center gap-2">
            <NeonButton
              size="sm"
              disabled={!dirty || editMutation.isPending}
              onClick={save}
            >
              {editMutation.isPending ? t("saving") : t("save")}
            </NeonButton>
            <NeonButton
              size="sm"
              variant="outline"
              onClick={() => setEditing(false)}
            >
              {t("cancel")}
            </NeonButton>
          </div>
        </div>
      )}
      {pending ? (
        <p
          className="text-xs mt-2 text-[var(--color-warning,#b45309)]"
          role="status"
        >
          {t("rebuildPending")}
        </p>
      ) : null}
      {done && !pending ? (
        <p className="text-xs mt-2 text-success" role="status">
          {t("success")}
        </p>
      ) : null}
    </div>
  );
}
