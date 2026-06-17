import { ParticleBackground } from "@/components/particle-background";

/**
 * Fixed full-viewport visual layers (grid drift, scanline overlay) plus the
 * animated particle field that sit behind the marketing page content.
 */
export function MarketingDecorations(): React.ReactElement {
  return (
    <>
      {/* Grid Background */}
      <div
        className="fixed inset-0 pointer-events-none z-0"
        aria-hidden="true"
        style={{ perspective: "600px", overflow: "hidden" }}
      >
        <div
          className="absolute inset-[-50%] w-[200%] h-[200%]"
          style={{
            backgroundImage: `linear-gradient(rgba(0, 212, 255, 0.025) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 212, 255, 0.025) 1px, transparent 1px)`,
            backgroundSize: "60px 60px",
            transform: "rotateX(60deg)",
            animation: "grid-drift 20s linear infinite",
          }}
        />
      </div>

      {/* Scanline Overlay */}
      <div
        className="fixed inset-0 pointer-events-none z-50"
        style={{
          background:
            "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0, 212, 255, 0.012) 2px, rgba(0, 212, 255, 0.012) 4px)",
        }}
      />

      {/* Particles */}
      <ParticleBackground />
    </>
  );
}
