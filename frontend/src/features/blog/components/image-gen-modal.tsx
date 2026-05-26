"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Alert, AlertDescription, Button, Input } from "@/components/ui";
import { useBlogAi } from "@/features/blog/hooks/use-blog-ai";

interface ImageGenModalProps {
  postId: string;
  open: boolean;
  onClose: () => void;
  onImageGenerated: (imageUrl: string) => void;
}

export function ImageGenModal({
  postId,
  open,
  onClose,
  onImageGenerated,
}: ImageGenModalProps): React.JSX.Element | null {
  const t = useTranslations("blogEditorial");
  const { generateImage, loading, error } = useBlogAi(postId);
  const [prompt, setPrompt] = useState("");
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  if (!open) {
    return null;
  }

  const handleGenerate = async (): Promise<void> => {
    const result = await generateImage(prompt);
    setPreviewUrl(result.image_url);
  };

  const handleUseImage = (): void => {
    if (previewUrl) {
      onImageGenerated(previewUrl);
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-full max-w-lg rounded-lg bg-background p-6 space-y-4">
        <h3 className="text-lg font-semibold">{t("imageModalTitle")}</h3>
        <Input
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          placeholder={t("imagePromptPlaceholder")}
        />
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        {previewUrl && (
          <img
            src={previewUrl}
            alt={t("generatedImageAlt")}
            className="w-full rounded-md border"
          />
        )}
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>
            {t("actions.cancel")}
          </Button>
          <Button
            disabled={loading || !prompt.trim()}
            onClick={() => void handleGenerate()}
          >
            {t("actions.generate")}
          </Button>
          <Button disabled={!previewUrl} onClick={handleUseImage}>
            {t("actions.useImage")}
          </Button>
        </div>
      </div>
    </div>
  );
}
