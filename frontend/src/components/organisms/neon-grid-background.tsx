export function NeonGridBackground(): React.ReactElement {
  return (
    <div
      className="fixed inset-0 pointer-events-none"
      aria-hidden="true"
      style={{ perspective: "600px", overflow: "hidden", zIndex: 0 }}
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
  );
}
