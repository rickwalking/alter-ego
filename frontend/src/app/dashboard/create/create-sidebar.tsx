import {
  BG_CARD,
  BG_DEEP,
  CYAN_GRADIENT,
  NEON_AMBER,
  NEON_AMBER_DIM,
  TEXT,
  TEXT_DIM,
} from "@/constants/neon";
import {
  CREATE_ARTIFACTS,
  CREATE_SUMMARY_ROWS,
} from "@/app/dashboard/create/constants";

const sidebarCardStyle = {
  background: BG_CARD,
  border: "1px solid rgba(255,255,255,0.06)",
  borderRadius: "8px",
  padding: "20px",
};

export function CreateSidebar(): React.ReactElement {
  return (
    <div
      style={{
        position: "sticky",
        top: "84px",
        alignSelf: "start",
        display: "flex",
        flexDirection: "column",
        gap: "16px",
      }}
    >
      <div style={sidebarCardStyle}>
        <h3 style={{ fontSize: "14px", fontWeight: 700, marginBottom: "12px" }}>
          Project Summary
        </h3>
        {CREATE_SUMMARY_ROWS.map((row) => (
          <div
            key={row.label}
            style={{
              display: "flex",
              justifyContent: "space-between",
              padding: "8px 0",
              fontSize: "13px",
              borderBottom: "1px solid rgba(255,255,255,0.03)",
            }}
          >
            <span style={{ color: TEXT_DIM }}>{row.label}</span>
            {"badge" in row && row.badge ? (
              <span
                style={{
                  padding: "2px 6px",
                  borderRadius: "4px",
                  fontSize: "11px",
                  fontWeight: 600,
                  background: NEON_AMBER_DIM,
                  color: NEON_AMBER,
                }}
              >
                {row.value}
              </span>
            ) : (
              <span style={{ color: TEXT, fontWeight: 600 }}>{row.value}</span>
            )}
          </div>
        ))}
      </div>

      <div style={sidebarCardStyle}>
        <h3 style={{ fontSize: "14px", fontWeight: 700, marginBottom: "12px" }}>
          Generation Report
        </h3>
        <div style={{ maxHeight: "400px", overflowY: "auto" }}>
          {CREATE_ARTIFACTS.map((artifact) => (
            <div
              key={artifact.name}
              style={{
                padding: "12px 0",
                borderBottom: "1px solid rgba(255,255,255,0.04)",
              }}
            >
              <h4
                style={{
                  fontSize: "12px",
                  fontWeight: 600,
                  color: TEXT,
                  margin: "0 0 4px",
                }}
              >
                {artifact.name}
              </h4>
              <p
                style={{
                  fontSize: "10px",
                  color: TEXT_DIM,
                  margin: 0,
                  lineHeight: 1.4,
                }}
              >
                {artifact.desc}
              </p>
              <span
                style={{
                  display: "inline-block",
                  fontSize: "9px",
                  padding: "1px 6px",
                  borderRadius: "3px",
                  fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                  marginTop: "6px",
                  background: NEON_AMBER_DIM,
                  color: NEON_AMBER,
                }}
              >
                {artifact.status}
              </span>
            </div>
          ))}
        </div>
      </div>

      <button
        type="button"
        style={{
          width: "100%",
          padding: "12px",
          borderRadius: "6px",
          border: "none",
          background: CYAN_GRADIENT,
          color: BG_DEEP,
          fontSize: "13px",
          fontWeight: 700,
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: "8px",
          fontFamily: "inherit",
        }}
      >
        Start Carousel
      </button>
    </div>
  );
}
