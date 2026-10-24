import type {
  SlideStructuredItemEdit,
  StructuredItemField,
} from "./presentation-slide-resolution";

/** The field a checklist slide shows for each item. */
export const CHECKLIST_ITEM_FIELD: StructuredItemField = "title";

/** Item fields a grid or list slide shows (title and body). */
export const DISPLAYED_ITEM_FIELDS: readonly StructuredItemField[] = [
  "title",
  "body",
];

/** The field a checklist slide shows only when the item has no title. */
const CHECKLIST_FALLBACK_FIELD: StructuredItemField = "body";

const HIDDEN_CHECKLIST_FIELDS: readonly StructuredItemField[] = [
  CHECKLIST_FALLBACK_FIELD,
];

function itemString(item: Record<string, unknown>, field: string): string {
  const value = item[field];
  return typeof value === "string" ? value : "";
}

/**
 * The line a checklist slide shows for an item: its title, else its body
 * (the same fallback the slide template uses).
 */
export function checklistItemText(item: Record<string, unknown>): string {
  return (
    itemString(item, CHECKLIST_ITEM_FIELD) ||
    itemString(item, CHECKLIST_FALLBACK_FIELD)
  );
}

/** An edit of a checklist line: it writes the title and empties the hidden body. */
export function checklistItemEdit(
  edit: Omit<SlideStructuredItemEdit, "field" | "clearFields">,
): SlideStructuredItemEdit {
  return {
    ...edit,
    field: CHECKLIST_ITEM_FIELD,
    clearFields: HIDDEN_CHECKLIST_FIELDS,
  };
}
