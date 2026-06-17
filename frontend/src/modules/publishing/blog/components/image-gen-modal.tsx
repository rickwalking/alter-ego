"use client";
import {
  NeonAlert,
  NeonAlertDescription,
} from "@/components/molecules/neon-alert";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonInput } from "@/components/atoms/neon-input";

import Image from "next/image";
import { useState } from "react";
import { useTranslations } from "next-intl";
import { useBlogAi } from "@/modules/publishing/blog/hooks/use-blog-ai";
import type { ImageGenModalProps } from "./types";

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
        <NeonInput
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          placeholder={t("imagePromptPlaceholder")}
        />
        {error && (
          <NeonAlert variant="destructive">
            <NeonAlertDescription>{error}</NeonAlertDescription>
          </NeonAlert>
        )}
        {previewUrl && (
          // The generated image's intrinsic dimensions are backend-configurable
          // and unknown to the frontend, so we use `fill` inside a fixed
          // aspect-ratio container with `object-contain` (shows the whole image
          // without cropping). `unoptimized` because the URL is a freshly
          // generated backend asset, not a known static remote pattern.
          <div className="relative aspect-square w-full overflow-hidden rounded-md border">
            <Image
              src={previewUrl}
              alt={t("generatedImageAlt")}
              fill
              className="object-contain"
              sizes="(min-width: 1024px) 32rem, 100vw"
              unoptimized
            />
          </div>
        )}
        <div className="flex justify-end gap-2">
          <NeonButton variant="outline" onClick={onClose}>
            {t("actions.cancel")}
          </NeonButton>
          <NeonButton
            disabled={loading || !prompt.trim()}
            onClick={() => void handleGenerate()}
          >
            {t("actions.generate")}
          </NeonButton>
          <NeonButton disabled={!previewUrl} onClick={handleUseImage}>
            {t("actions.useImage")}
          </NeonButton>
        </div>
      </div>
    </div>
  );
}
