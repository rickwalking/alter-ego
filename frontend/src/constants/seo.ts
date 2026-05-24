/** SEO preview constants (UI-025). */

export const SEO_TITLE_MIN = 30;
export const SEO_TITLE_MAX = 60;
export const SEO_DESCRIPTION_MIN = 70;
export const SEO_DESCRIPTION_MAX = 160;

export const SEO_PREVIEW_GOOGLE = "google";
export const SEO_PREVIEW_TWITTER = "twitter";
export const SEO_PREVIEW_LINKEDIN = "linkedin";

export type SeoPreviewPlatform =
  | typeof SEO_PREVIEW_GOOGLE
  | typeof SEO_PREVIEW_TWITTER
  | typeof SEO_PREVIEW_LINKEDIN;
