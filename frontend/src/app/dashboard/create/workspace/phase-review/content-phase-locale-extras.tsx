"use client";

import {
  editableStructuredListKey,
  isPresentationStructuredItemList,
  listPresentationStructuredItems,
  listStructuredExtras,
  mirrorLocaleStructure,
  otherLocaleKey,
  PRESENTATION_STRUCTURED_ITEM_LIST_KEYS,
  PresentationStructuredItems,
  type PresentationLocaleKey,
  type SlideCopyEdit,
  type SlideExtraEdit,
  type SlideFieldErrors,
  type SlideStructuredItemEdit,
  type SlideStructuredListEdit,
} from "@/modules/editorial";
import type { LocalizedSlideReview } from "@/modules/publishing";

import { IconRow, ReadOnlyExtra } from "./content-phase-readonly-extras";
import {
  EditableStructuredExtra,
  EditableStructuredItems,
  isEditableExtra,
  type StructuredEditContext,
} from "./content-phase-structured-fields";

export interface StructuredList {
  listKey: string;
  items: Record<string, unknown>[];
}

export function structuredList(
  presentation: Record<string, unknown>,
): StructuredList | null {
  for (const listKey of PRESENTATION_STRUCTURED_ITEM_LIST_KEYS) {
    const value = presentation[listKey];
    if (isPresentationStructuredItemList(value)) {
      return { listKey, items: value as Record<string, unknown>[] };
    }
  }
  return null;
}

/**
 * AE-0437: the list an editable column edits — the slide type's own key (a
 * closing slide edits ``actions``), offered even when empty.
 */
export function editableList(
  presentation: Record<string, unknown>,
  slideType: string,
): StructuredList | null {
  const listKey = editableStructuredListKey(presentation, slideType);
  if (!listKey) {
    return null;
  }
  const value = presentation[listKey];
  const items = isPresentationStructuredItemList(value)
    ? (value as Record<string, unknown>[])
    : [];
  return { listKey, items };
}

export function editContext(
  props: ContentLocaleFieldsProps,
): StructuredEditContext | null {
  if (!props.onStructuredItemChange || !props.onExtraChange) {
    return null;
  }
  return {
    slide: props.slide,
    localeKey: props.localeKey,
    policyVersion: props.policyVersion,
    fieldErrors: props.fieldErrors,
    onItemChange: props.onStructuredItemChange,
    onExtraChange: props.onExtraChange,
    onListChange: props.onStructuredListChange,
  };
}

export function PresentationExtras({
  props,
}: {
  props: ContentLocaleFieldsProps;
}): React.ReactElement {
  const context = editContext(props);
  // AE-0430: an editable column also offers every structured field the
  // other locale has (an EN TL;DR the translation dropped stays fixable).
  const presentation = context
    ? mirrorLocaleStructure(
        props.slide[props.localeKey],
        props.slide[otherLocaleKey(props.localeKey)],
      )
    : props.slide[props.localeKey];
  const list = context
    ? editableList(presentation, props.slide.slide_type)
    : structuredList(presentation);
  const extras = listStructuredExtras(presentation);
  return (
    <>
      {context ? null : (
        <IconRow presentation={presentation} localeLabel={props.localeLabel} />
      )}
      {list && context ? (
        <EditableStructuredItems
          context={context}
          listKey={list.listKey}
          items={list.items}
        />
      ) : null}
      {list && !context ? (
        <PresentationStructuredItems
          items={listPresentationStructuredItems(presentation)}
        />
      ) : null}
      {extras.length > 0 ? (
        <div className="space-y-1 pt-1">
          {extras.map((extra) =>
            context && isEditableExtra(extra.key, extra.value) ? (
              <EditableStructuredExtra
                key={`${props.localeLabel}-${extra.key}`}
                context={context}
                extraKey={extra.key}
                value={extra.value}
              />
            ) : (
              <ReadOnlyExtra
                key={`${props.localeLabel}-${extra.key}`}
                extraKey={extra.key}
                value={extra.value}
              />
            ),
          )}
        </div>
      ) : null}
    </>
  );
}

export interface ContentLocaleFieldsProps {
  slide: LocalizedSlideReview;
  localeKey: PresentationLocaleKey;
  localeLabel: string;
  /** AE-0414: drives the copy budgets (every policy version has them). */
  policyVersion?: string | null;
  /** Present only while the content step is editable. */
  onCopyChange?: (edit: SlideCopyEdit) => void;
  /** AE-0414 (B11): structured items are editable with the copy. */
  onStructuredItemChange?: (edit: SlideStructuredItemEdit) => void;
  /** AE-0414 (B11): free-text extras (tldr, CTA fields, insight text). */
  onExtraChange?: (edit: SlideExtraEdit) => void;
  /** AE-0437: add / remove structured item slots. */
  onStructuredListChange?: (edit: SlideStructuredListEdit) => void;
  fieldErrors: SlideFieldErrors;
}
