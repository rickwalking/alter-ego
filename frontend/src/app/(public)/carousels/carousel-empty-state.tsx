import { TEXT, TEXT_MUTED } from "@/constants/neon";
import { CarouselPlaceholderIcon } from "./carousel-placeholder-icon";

interface CarouselEmptyStateProps {
  title: string;
  hint: string;
}

/** Empty gallery state (AE-0444). */
export function CarouselEmptyState({
  title,
  hint,
}: CarouselEmptyStateProps): React.ReactElement {
  return (
    <div
      className="rounded-xl border border-dashed px-6 py-16 text-center"
      style={{ borderColor: "rgba(255,255,255,0.12)" }}
    >
      <CarouselPlaceholderIcon size={40} className="mx-auto mb-4 opacity-60" />
      <p className="text-base font-semibold" style={{ color: TEXT }}>
        {title}
      </p>
      <p className="mt-2 text-sm" style={{ color: TEXT_MUTED }}>
        {hint}
      </p>
    </div>
  );
}
