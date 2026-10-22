"use client";

import { Fragment, type ReactNode } from "react";
import {
  NeonDeleteConfirm,
  type NeonDeleteConfirmProps,
} from "@/components/molecules/neon-delete-confirm";
import type { EditableEntity, EntityEditor } from "@/lib/use-entity-editor";

export interface NeonEntityWorkspaceProps<T extends EditableEntity, P> {
  editor: EntityEditor<T, P>;
  /** The page's `<entity>.delete` translator. */
  deleteT: NeonDeleteConfirmProps["t"];
  list: ReactNode;
  renderForm: (editing: T | undefined) => ReactNode;
}

/** A collection page body: the list or the open form, plus the delete confirmation. */
export function NeonEntityWorkspace<T extends EditableEntity, P>({
  editor,
  deleteT,
  list,
  renderForm,
}: Readonly<NeonEntityWorkspaceProps<T, P>>): React.ReactElement {
  const { item, onConfirm, onClose } = editor.deleteActions;
  return (
    <>
      {editor.showingList ? (
        list
      ) : (
        <Fragment key={editor.formKey}>{renderForm(editor.editing)}</Fragment>
      )}
      {item && (
        <NeonDeleteConfirm
          t={deleteT}
          name={item.name}
          onConfirm={() => onConfirm(item)}
          onClose={onClose}
        />
      )}
    </>
  );
}
