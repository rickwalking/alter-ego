import Link from "next/link";
import type { BlogLanguageSwitchProps } from "./types";

/**
 * PT/EN content buttons on a public post (AE-0423, ADR-0025). They switch the
 * rendered document via `?lang=` (content language) and leave the next-intl
 * UI locale untouched. Labels and hrefs come from the page (dumb component).
 */
export function BlogLanguageSwitch({
  activeLanguage,
  label,
  options,
}: BlogLanguageSwitchProps) {
  return (
    <nav aria-label={label} className="mb-6 flex gap-2">
      {options.map((option) => {
        const active = option.language === activeLanguage;
        return (
          <Link
            key={option.language}
            href={option.href}
            aria-current={active ? "true" : undefined}
            className={`rounded-full border px-3 py-1 text-xs font-semibold no-underline transition-opacity ${
              active ? "opacity-100" : "opacity-60 hover:opacity-90"
            }`}
          >
            {option.label}
          </Link>
        );
      })}
    </nav>
  );
}
