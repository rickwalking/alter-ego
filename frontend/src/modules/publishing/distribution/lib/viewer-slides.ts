import type { CarouselProjectResponse } from "@/schemas/carousel";
import type {
  ViewerLanguage,
  ViewerSlideSource,
} from "@/modules/publishing/distribution/types";

const LANGUAGE_EN: ViewerLanguage = "en";

interface DesignTokenImages {
  slides?: string[];
  rendered_slides_pt?: string[];
  rendered_slides_en?: string[];
}

function designTokenSlidePaths(
  project: CarouselProjectResponse,
  language: ViewerLanguage,
): string[] {
  const tokens = project.design_tokens as
    | { images?: DesignTokenImages }
    | null
    | undefined;
  // The publish viewer wants the RENDERED slides (with text overlay),
  // not the raw hero images. Fall back to legacy `slides` for projects
  // generated before the rendered_slides_* fields existed.
  const ptSlides =
    tokens?.images?.rendered_slides_pt ?? tokens?.images?.slides ?? [];
  const enSlides = tokens?.images?.rendered_slides_en ?? ptSlides;
  return language === LANGUAGE_EN ? enSlides : ptSlides;
}

/**
 * AE-0416 (B25): one `slide_N.jpg` per real slide of the project, so an
 * 8-slide deck shows "1 / 8" even when the stored design tokens still list an
 * older render. Without a slide list it falls back to the design tokens.
 */
export function viewerSlidePaths(source: ViewerSlideSource): string[] {
  const numbers = source.slideNumbers ?? [];
  if (numbers.length > 0) {
    return [...numbers]
      .sort((left, right) => left - right)
      .map((slideNumber) => `slide_${slideNumber}.jpg`);
  }
  return designTokenSlidePaths(source.project, source.language);
}

/** Title used in the slide alt text, in the viewer's language (AE-0416). */
export function viewerSlideTitle(
  project: CarouselProjectResponse,
  language: ViewerLanguage,
): string {
  const ptTitle = project.title || project.topic;
  return language === LANGUAGE_EN ? project.title_en || ptTitle : ptTitle;
}
