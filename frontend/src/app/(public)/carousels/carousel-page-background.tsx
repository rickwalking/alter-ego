import { NEON_CYAN_DIM, NEON_MAGENTA_DIM } from "@/constants/neon";

/** Ambient neon glow shared by the public carousel pages (AE-0444). */
export function CarouselPageBackground(): React.ReactElement {
  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0">
      <div
        className="absolute -top-32 right-0 h-[420px] w-[420px] rounded-full blur-3xl"
        style={{ background: NEON_CYAN_DIM }}
      />
      <div
        className="absolute bottom-0 left-0 h-[320px] w-[320px] rounded-full blur-3xl"
        style={{ background: NEON_MAGENTA_DIM }}
      />
    </div>
  );
}
