import { TEXT_DIM } from "@/constants/neon";

export function MarketingFooter(): React.ReactElement {
  return (
    <>
      <footer
        style={{
          position: "relative",
          zIndex: 1,
          borderTop: `1px solid rgba(0,212,255,0.06)`,
          padding: "40px 0",
          background: "rgba(6,10,18,0.5)",
        }}
      >
        <div
          className="mx-auto px-6"
          style={{
            maxWidth: "1200px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            fontFamily: "'JetBrains Mono', ui-monospace, monospace",
            fontSize: "11px",
            color: TEXT_DIM,
          }}
        >
          <span>© 2026 Pedro Marins</span>
        </div>
      </footer>

      {/* Landing particle drift — distinct from globals.css particle-float used elsewhere */}
      <style>{`
        @keyframes particle-float-landing {
          0% { transform: translateY(0) translateX(0); opacity: 0; }
          10% { opacity: 1; }
          90% { opacity: 1; }
          100% { transform: translateY(-100vh) translateX(100px); opacity: 0; }
        }
      `}</style>
    </>
  );
}
