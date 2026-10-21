import Link from "next/link";
import { NEON_CYAN, NEON_CYAN_DIM, TEXT_MUTED } from "@/constants/neon";

export interface CarouselLanguageOption {
  language: string;
  label: string;
  href: string;
}

interface CarouselLanguageSwitchProps {
  activeLanguage: string;
  label: string;
  options: CarouselLanguageOption[];
}

/** PT/EN content links on a public carousel viewer (AE-0444). */
export function CarouselLanguageSwitch({
  activeLanguage,
  label,
  options,
}: CarouselLanguageSwitchProps): React.ReactElement {
  return (
    <nav
      aria-label={label}
      className="mt-6 flex items-center justify-center gap-2"
    >
      {options.map((option) => {
        const active = option.language === activeLanguage;
        return (
          <Link
            key={option.language}
            href={option.href}
            aria-current={active ? "true" : undefined}
            className="rounded-full border px-3 py-1 font-mono text-xs font-semibold no-underline transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-neon-cyan"
            style={{
              borderColor: active ? NEON_CYAN : NEON_CYAN_DIM,
              background: active ? NEON_CYAN_DIM : "transparent",
              color: active ? NEON_CYAN : TEXT_MUTED,
            }}
          >
            {option.label}
          </Link>
        );
      })}
    </nav>
  );
}
