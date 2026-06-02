import {
  NEON_CYAN,
  NEON_PROGRESS_GLOW,
  TEXT_DIM,
  TEXT_MUTED,
} from "@/constants/neon";
export interface NeonProgressBarComponentProps {
  value: number;
  max?: number;
  label?: string;
}

export function NeonProgressBar({
  value,
  max = 100,
  label,
}: NeonProgressBarComponentProps): React.ReactElement {
  const percent = Math.min(100, Math.max(0, (value / max) * 100));

  return (
    <div className="w-full space-y-2">
      {label && (
        <div
          className="flex justify-between text-xs"
          style={{ color: TEXT_MUTED }}
        >
          <span>{label}</span>
          <span style={{ color: TEXT_DIM }}>{Math.round(percent)}%</span>
        </div>
      )}
      <div
        className="h-2 w-full rounded-full overflow-hidden"
        style={{ background: "rgba(255,255,255,0.06)" }}
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={max}
      >
        <div
          className="h-full rounded-full transition-all duration-300"
          style={{
            width: `${percent}%`,
            background: NEON_CYAN,
            boxShadow: NEON_PROGRESS_GLOW,
          }}
        />
      </div>
    </div>
  );
}
