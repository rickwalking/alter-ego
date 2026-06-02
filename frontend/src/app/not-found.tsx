import Link from "next/link";
import { getTranslations } from "next-intl/server";
import {
  NeonGridBackground,
  NeonScanlineOverlay,
} from "@/components/organisms";
import { BG_DEEP, CYAN_GRADIENT, TEXT, TEXT_MUTED } from "@/constants/neon";
import { PUBLIC_ROUTE_PATHS } from "@/constants/public-routes";

export default async function NotFound(): Promise<React.ReactElement> {
  const t = await getTranslations("notFound");

  return (
    <div
      className="relative flex min-h-screen flex-col items-center justify-center px-4 text-center"
      style={{ background: BG_DEEP, color: TEXT }}
    >
      <NeonGridBackground />
      <NeonScanlineOverlay />
      <div style={{ position: "relative", zIndex: 1, maxWidth: "480px" }}>
        <h1
          style={{
            fontSize: "clamp(40px, 8vw, 72px)",
            fontWeight: 900,
            letterSpacing: "-0.03em",
            lineHeight: 1,
            marginBottom: "16px",
            background: CYAN_GRADIENT,
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            backgroundClip: "text",
          }}
        >
          {t("code")}
        </h1>
        <h2 style={{ fontSize: "22px", fontWeight: 700, marginBottom: "8px" }}>
          {t("title")}
        </h2>
        <p
          style={{ fontSize: "15px", color: TEXT_MUTED, marginBottom: "32px" }}
        >
          {t("description")}
        </p>
        <Link
          href={PUBLIC_ROUTE_PATHS.HOME}
          style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "12px 28px",
            borderRadius: "6px",
            fontSize: "14px",
            fontWeight: 600,
            textDecoration: "none",
            background: CYAN_GRADIENT,
            color: BG_DEEP,
            boxShadow: "0 0 20px rgba(0,212,255,0.15)",
          }}
        >
          {t("goHome")}
        </Link>
      </div>
    </div>
  );
}
