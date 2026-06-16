"use client";

import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { useEffect } from "react";
import { cn } from "@/lib/utils";
import type { RichTextEditorProps } from "./types";

export function RichTextEditor({
  value,
  onChange,
  onSelectionChange,
  className,
  placeholder,
}: RichTextEditorProps): React.JSX.Element {
  const editor = useEditor({
    extensions: [StarterKit],
    content: value,
    immediatelyRender: false,
    editorProps: {
      attributes: {
        class:
          "prose prose-sm dark:prose-invert min-h-[200px] max-w-none focus:outline-none px-3 py-2",
      },
    },
    onUpdate: ({ editor: currentEditor }) => {
      onChange(currentEditor.getText());
    },
    onSelectionUpdate: ({ editor: currentEditor }) => {
      if (!onSelectionChange) {
        return;
      }
      const { from, to } = currentEditor.state.selection;
      onSelectionChange(currentEditor.state.doc.textBetween(from, to, " "));
    },
  });

  useEffect(() => {
    if (!editor) {
      return;
    }
    const current = editor.getText();
    if (value !== current) {
      editor.commands.setContent(value);
    }
  }, [editor, value]);

  return (
    <div
      className={cn(
        "rounded-md border border-[var(--color-border)] bg-[var(--color-background)]",
        className,
      )}
    >
      {placeholder && !value && (
        <p className="pointer-events-none px-3 pt-2 text-muted-foreground text-sm">
          {placeholder}
        </p>
      )}
      <EditorContent editor={editor} />
    </div>
  );
}
