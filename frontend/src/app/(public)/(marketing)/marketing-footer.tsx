import Link from "next/link";
import { TEXT_DIM } from "@/constants/neon";
import { PUBLIC_ROUTE_PATHS } from "@/constants/public-routes";

/**
 * Copyright and the privacy policy link. Also defines the landing particle
 * drift keyframes, distinct from the `particle-float` in globals.css used
 * elsewhere.
 */
export function MarketingFooter({
  privacyLabel,
}: Readonly<{ privacyLabel: string }>): React.ReactElement {
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
          <span style={{ display: "flex", gap: "16px", alignItems: "center" }}>
            <span>© 2026 Pedro Marins</span>
            <Link
              href={PUBLIC_ROUTE_PATHS.PRIVACY}
              className="underline-offset-4 hover:underline"
              style={{ color: TEXT_DIM }}
            >
              {privacyLabel}
            </Link>
          </span>
        </div>
      </footer>

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
