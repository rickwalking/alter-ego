import { countHashtags } from "@/modules/publishing/distribution/components/caption-editor";

export const IG_MAX_CHARS = 2200;
export const IG_MAX_HASHTAGS = 30;
export const LINKEDIN_MAX_CHARS = 3000;

/** The caption breaks an Instagram limit (length or hashtag count). */
export function captionInvalid(caption: string): boolean {
  return (
    caption.length > IG_MAX_CHARS || countHashtags(caption) > IG_MAX_HASHTAGS
  );
}

/** The LinkedIn post is over the platform's length limit. */
export function linkedinInvalid(text: string): boolean {
  return text.length > LINKEDIN_MAX_CHARS;
}
