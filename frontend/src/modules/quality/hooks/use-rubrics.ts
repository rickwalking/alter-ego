/**
 * Custom hook for managing quality rubrics
 */

import {
  useResourceCollection,
  type ResourceCollection,
} from "@/lib/use-resource-collection";
import type {
  QualityRubric,
  QualityRubricCreatePayload,
  QualityRubricUpdatePayload,
} from "@/modules/quality/types";

type RubricsCollection = Omit<
  ResourceCollection<
    QualityRubric,
    QualityRubricCreatePayload,
    QualityRubricUpdatePayload
  >,
  "items"
> & { rubrics: QualityRubric[] };

/** The rubrics collection (list, create, update, delete). */
export function useRubrics(): RubricsCollection {
  const { items, ...rest } = useResourceCollection<
    QualityRubric,
    QualityRubricCreatePayload,
    QualityRubricUpdatePayload
  >({
    path: "rubrics",
    noun: "rubric",
  });
  return { rubrics: items, ...rest };
}
