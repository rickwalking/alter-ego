"use client";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonInput } from "@/components/atoms/neon-input";
import { NeonTextarea } from "@/components/atoms/neon-textarea";
import { NeonLabel } from "@/components/atoms/neon-label";
import { NeonBadge } from "@/components/atoms/neon-badge";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { X } from "lucide-react";
import { type CreateDocumentRequest } from "@/schemas/knowledge";

interface DocumentFormProps {
  onSubmit: (data: CreateDocumentRequest) => void;
  onCancel: () => void;
}

export function DocumentForm({ onSubmit, onCancel }: DocumentFormProps) {
  const t = useTranslations("knowledge");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [newTag, setNewTag] = useState("");

  const handleAddTag = () => {
    if (newTag.trim() && !tags.includes(newTag.trim())) {
      setTags([...tags, newTag.trim()]);
      setNewTag("");
    }
  };

  const handleRemoveTag = (tagToRemove: string) => {
    setTags(tags.filter((tag) => tag !== tagToRemove));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      title: title.trim(),
      content: content.trim(),
      metadata: { tags },
    });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="space-y-2">
        <NeonLabel htmlFor="title">{t("form.title")}</NeonLabel>
        <NeonInput
          id="title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder={t("form.titlePlaceholder")}
          required
        />
      </div>

      <div className="space-y-2">
        <NeonLabel htmlFor="content">{t("form.content")}</NeonLabel>
        <NeonTextarea
          id="content"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder={t("form.contentPlaceholder")}
          rows={10}
          required
        />
      </div>

      <div className="space-y-2">
        <NeonLabel>{t("form.tags")}</NeonLabel>
        <div className="flex gap-2">
          <NeonInput
            value={newTag}
            onChange={(e) => setNewTag(e.target.value)}
            placeholder={t("form.tagPlaceholder")}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                handleAddTag();
              }
            }}
          />
          <NeonButton type="button" onClick={handleAddTag} variant="secondary">
            {t("form.addTag")}
          </NeonButton>
        </div>
        {tags.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-2">
            {tags.map((tag) => (
              <NeonBadge key={tag} variant="secondary" className="gap-1">
                {tag}
                <button
                  type="button"
                  onClick={() => handleRemoveTag(tag)}
                  className="ml-1 hover:text-[var(--color-destructive)]"
                >
                  <X className="h-3 w-3" />
                </button>
              </NeonBadge>
            ))}
          </div>
        )}
      </div>

      <div className="flex justify-end gap-4">
        <NeonButton type="button" variant="outline" onClick={onCancel}>
          {t("form.cancel")}
        </NeonButton>
        <NeonButton type="submit">{t("form.submit")}</NeonButton>
      </div>
    </form>
  );
}
