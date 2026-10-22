"use client";

import { useState } from "react";

/** A named record a dashboard page lists, edits and deletes. */
export interface EditableEntity {
  id: string;
  name: string;
}

/** The writes of a REST collection the editor drives. */
export interface EntityEditorWrites<P> {
  create: (data: P) => Promise<unknown>;
  update: (id: string, data: P) => Promise<unknown>;
  delete: (id: string) => Promise<boolean>;
}

type EditorView<T> =
  | { kind: "list" }
  | { kind: "create" }
  | { kind: "edit"; item: T };

const LIST_VIEW = { kind: "list" } as const;

export interface EntityDeleteActions<T> {
  /** The item awaiting confirmation; null while nothing is being deleted. */
  item: T | null;
  onConfirm: (item: T) => Promise<void>;
  onClose: () => void;
}

export interface EntityEditor<T extends EditableEntity, P> {
  showingList: boolean;
  /** The item open in the form; undefined while creating. */
  editing: T | undefined;
  /** Remounts the form whenever a different item (or a new one) opens. */
  formKey: string;
  listActions: {
    onCreate: () => void;
    onEdit: (item: T) => void;
    onDelete: (item: T) => void;
  };
  formActions: {
    onSave: (payload: P) => Promise<void>;
    onCancel: () => void;
  };
  deleteActions: EntityDeleteActions<T>;
}

/** The delete confirmation: open on an item, closed once the delete succeeds. */
function useDeleteConfirmation<T extends EditableEntity>(
  remove: (id: string) => Promise<boolean>,
): EntityDeleteActions<T> & { open: (item: T) => void } {
  const [item, setItem] = useState<T | null>(null);
  return {
    item,
    open: setItem,
    onConfirm: async (target) => {
      await remove(target.id);
      setItem(null);
    },
    onClose: () => setItem(null),
  };
}

/**
 * The list ⇄ create/edit form switch and the delete confirmation of a
 * dashboard collection page: a save returns to the list, a delete closes
 * the confirmation.
 */
export function useEntityEditor<T extends EditableEntity, P>(
  writes: EntityEditorWrites<P>,
): EntityEditor<T, P> {
  const [view, setView] = useState<EditorView<T>>(LIST_VIEW);
  const { open, ...deleteActions } = useDeleteConfirmation<T>(writes.delete);
  const editing = view.kind === "edit" ? view.item : undefined;
  const showList = (): void => setView(LIST_VIEW);

  const save = async (payload: P): Promise<void> => {
    if (editing) {
      await writes.update(editing.id, payload);
    } else {
      await writes.create(payload);
    }
    showList();
  };

  return {
    showingList: view.kind === "list",
    editing,
    formKey: editing?.id ?? view.kind,
    listActions: {
      onCreate: () => setView({ kind: "create" }),
      onEdit: (item) => setView({ kind: "edit", item }),
      onDelete: open,
    },
    formActions: { onSave: save, onCancel: showList },
    deleteActions,
  };
}
