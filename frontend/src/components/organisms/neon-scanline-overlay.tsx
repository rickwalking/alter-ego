export function NeonScanlineOverlay(): React.ReactElement {
  return (
    <div
      className="fixed inset-0 pointer-events-none"
      style={{
        zIndex: 50,
        background:
          "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0, 212, 255, 0.012) 2px, rgba(0, 212, 255, 0.012) 4px)",
      }}
      aria-hidden="true"
    />
  );
}
