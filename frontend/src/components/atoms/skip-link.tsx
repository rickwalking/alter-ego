import { useTranslations } from "next-intl";

import { MAIN_CONTENT_ID } from "@/constants/a11y";

/**
 * First focusable element of a shell: hidden until focused, it jumps keyboard
 * and screen-reader users past the header/sidebar to the page's `<main>`.
 */
export function SkipLink(): React.ReactElement {
  const t = useTranslations("common");
  return (
    <a
      href={`#${MAIN_CONTENT_ID}`}
      className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[200] focus:rounded-md focus:bg-neon-cyan focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-bg-deep"
    >
      {t("skipToContent")}
    </a>
  );
}
