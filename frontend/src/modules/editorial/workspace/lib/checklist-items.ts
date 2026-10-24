import type {
  SlideStructuredItemEdit,
  StructuredItemField,
} from "./presentation-slide-resolution";
import { PRESENTATION_STRUCTURED_ITEM_LIST_KEYS } from "./presentation-review-utils";

/** Lines a checklist slide shows at most (the template's ``SAVE_CHECKLIST_MAX_ITEMS``). */
export const CHECKLIST_MAX_ITEMS = 5;

/** One line on a checklist slide and the item it comes from. */
export interface ChecklistLine {
  itemIndex: number;
  text: string;
}

/** The list a checklist slide draws and the lines it shows. */
export interface ChecklistLines {
  listKey: string;
  lines: ChecklistLine[];
}

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

function itemRecord(item: unknown): Record<string, unknown> | null {
  return item && typeof item === "object" && !Array.isArray(item)
    ? (item as Record<string, unknown>)
    : null;
}

function linesOf(items: unknown[]): ChecklistLine[] {
  return items.flatMap((item, itemIndex) => {
    const record = itemRecord(item);
    const text = record ? checklistItemText(record) : "";
    return text.trim() ? [{ itemIndex, text }] : [];
  });
}

/**
 * What a checklist slide draws, as the template does: the first list (in
 * template order) with a non-blank line, its blank items dropped, at most
 * ``CHECKLIST_MAX_ITEMS`` lines. ``null`` when no list has a line.
 */
export function checklistLines(
  presentation: Record<string, unknown>,
): ChecklistLines | null {
  for (const listKey of PRESENTATION_STRUCTURED_ITEM_LIST_KEYS) {
    const value = presentation[listKey];
    const lines = Array.isArray(value) ? linesOf(value) : [];
    if (lines.length > 0) {
      return { listKey, lines: lines.slice(0, CHECKLIST_MAX_ITEMS) };
    }
  }
  return null;
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
