"use client";

import { useCallback, useState } from "react";
import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { TEXT_DIM } from "@/constants/neon";
import {
  addressViolations,
  applySlideCopyEdit,
  applySlideStructuredItemEdit,
  BlockingSlidesNotice,
  buildSlideFieldErrors,
  fieldErrorKey,
  focusInvalidField,
  SlideCopyEditor,
  slidesHaveCopyChanges,
  structuredItemFieldPath,
  useSlideFieldErrors,
  type SlideCopyEdit,
  type SlideStructuredItemEdit,
  type SlideValidationViolation,
} from "@/modules/editorial";
import { SECTION_CARD_STYLE } from "@/modules/publishing/distribution/constants";
import {
  useEditCarouselSlides,
  type EditCarouselSlidesResponse,
} from "@/modules/publishing/distribution/hooks/use-edit-carousel-slides";
import { useRepublishCarousel } from "@/modules/publishing/distribution/hooks/use-republish-carousel";
import type { LocalizedSlideReview } from "@/modules/publishing/blog/types-ai";
import type { SlideTextEditSectionProps } from "./types";
import {
  RunInProgressCard,
  SlideEditActions,
  SlideEditStatus,
} from "./slide-text-edit-parts";

const EDIT_ID_PREFIX = "publish-edit";
const NO_VIOLATIONS: SlideValidationViolation[] = [];

/** The refused save's violations, each addressed to its field. */
function responseViolations(
  data: EditCarouselSlidesResponse,
): SlideValidationViolation[] {
  return addressViolations(data.field_violations ?? []);
}

export function SlideTextEditSection(
  props: Readonly<SlideTextEditSectionProps>,
): React.ReactElement {
  const { projectId, slides, policyVersion, runInProgress, onEdited } = props;
  const t = useTranslations("publish.slideEditor");
  const editMutation = useEditCarouselSlides();
  const republish = useRepublishCarousel();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<LocalizedSlideReview[]>(slides);
  const [violations, setViolations] = useState(NO_VIOLATIONS);
  const [refused, setRefused] = useState(false);
  const [fixedSinceRefusal, setFixedSinceRefusal] = useState(false);
  const [validationCount, setValidationCount] = useState(0);
  const [done, setDone] = useState(false);
  const errors = useSlideFieldErrors(violations, String(validationCount));
  const { clearField } = errors;

  const open = useCallback(() => {
    setDraft(slides);
    setViolations(NO_VIOLATIONS);
    setRefused(false);
    setDone(false);
    setEditing(true);
  }, [slides]);

  const onCopyChange = useCallback(
    (edit: SlideCopyEdit) => {
      setDraft((current) => applySlideCopyEdit(current, edit));
      clearField(fieldErrorKey(edit.slideIndex, edit.locale, edit.field));
      setFixedSinceRefusal(true);
    },
    [clearField],
  );

  const onStructuredItemChange = useCallback(
    (edit: SlideStructuredItemEdit) => {
      setDraft((current) => applySlideStructuredItemEdit(current, edit));
      const path = structuredItemFieldPath(
        edit.listKey,
        edit.itemIndex,
        edit.field,
      );
      clearField(fieldErrorKey(edit.slideIndex, edit.locale, path));
      setFixedSinceRefusal(true);
    },
    [clearField],
  );

  const onRefused = useCallback((next: SlideValidationViolation[]) => {
    setViolations(next);
    setValidationCount((count) => count + 1);
    setRefused(true);
    setFixedSinceRefusal(false);
    focusInvalidField(EDIT_ID_PREFIX, buildSlideFieldErrors(next));
  }, []);

  const save = useCallback(() => {
    editMutation.mutate(
      { projectId, editedSlides: draft },
      {
        onSuccess: (data) => {
          if (data.validation.blocking === true) {
            onRefused(responseViolations(data));
            return;
          }
          setViolations(NO_VIOLATIONS);
          setRefused(false);
          setEditing(false);
          setDone(true);
          republish.mutate({ projectId }, { onSuccess: () => onEdited() });
        },
      },
    );
  }, [projectId, draft, editMutation, republish, onEdited, onRefused]);

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
            idPrefix={EDIT_ID_PREFIX}
            policyVersion={policyVersion}
            showBudget
            onCopyChange={onCopyChange}
            onStructuredItemChange={onStructuredItemChange}
            fieldErrors={errors.fieldErrors}
            violations={errors.open}
          />
          {refused ? (
            <BlockingSlidesNotice
              message={t("blockingViolations")}
              slideIndexes={errors.slideIndexes}
              onSelectSlide={(slideIndex) =>
                focusInvalidField(
                  EDIT_ID_PREFIX,
                  errors.fieldErrors,
                  slideIndex,
                )
              }
            />
          ) : null}
          <SlideEditActions
            refused={refused}
            canSave={refused ? fixedSinceRefusal : dirty}
            saving={editMutation.isPending}
            onSave={save}
            onCancel={() => setEditing(false)}
          />
        </div>
      )}
      <SlideEditStatus pending={pending} done={done} />
    </div>
  );
}
