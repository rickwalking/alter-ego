import {
  BG_CARD,
  NEON_CYAN,
  NEON_CYAN_DIM,
  TEXT,
  TEXT_DIM,
} from "@/constants/neon";
import { CREATE_STEPS } from "@/app/dashboard/create/constants";

const CYAN = NEON_CYAN;
const CYAN_DIM = NEON_CYAN_DIM;

export function CreateProgressSteps(): React.ReactElement {
  return (
    <div
      style={{
        display: "flex",
        marginBottom: "28px",
        background: BG_CARD,
        borderRadius: "8px",
        border: "1px solid rgba(255,255,255,0.06)",
        overflow: "hidden",
      }}
    >
      {CREATE_STEPS.map((step) => (
        <div
          key={step.num}
          style={{
            flex: 1,
            padding: "12px 16px",
            display: "flex",
            alignItems: "center",
            gap: "8px",
            fontSize: "12px",
            color: step.num === 1 ? TEXT : TEXT_DIM,
            borderRight:
              step.num < CREATE_STEPS.length
                ? "1px solid rgba(255,255,255,0.04)"
                : "none",
          }}
        >
          <span
            style={{
              width: "20px",
              height: "20px",
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontFamily: "'JetBrains Mono', ui-monospace, monospace",
              fontSize: "10px",
              fontWeight: 700,
              flexShrink: 0,
              background: step.num === 1 ? CYAN_DIM : "rgba(255,255,255,0.04)",
              color: step.num === 1 ? CYAN : TEXT_DIM,
            }}
          >
            {step.num}
          </span>
          <span>{step.label}</span>
        </div>
      ))}
    </div>
  );
}
