"use client";

import { useTranslations } from "next-intl";
import {
  NeonGridBackground,
  NeonScanlineOverlay,
} from "@/components/organisms";
import { BG_DEEP, TEXT } from "@/constants/neon";
import { LoginFooter, LoginHeader } from "./login-chrome";
import { LoginForm } from "./login-form";
import { LoginHero } from "./login-hero";
import { useLogin } from "./use-login";

export default function LoginPage() {
  const t = useTranslations("auth");
  const login = useLogin();

  return (
    <div
      className="min-h-screen flex flex-col"
      style={{
        background: BG_DEEP,
        color: TEXT,
        fontFamily: "Inter, system-ui, sans-serif",
      }}
    >
      <NeonGridBackground />
      <NeonScanlineOverlay />

      <LoginHeader />

      <main className="flex-1 flex items-center justify-center relative z-10 px-4">
        <div style={{ width: "100%", maxWidth: "420px" }}>
          <LoginHero title={t("loginTitle")} subtitle={t("loginSubtitle")} />
          <LoginForm {...login} />
        </div>
      </main>

      <LoginFooter />

      <style>{`
        @keyframes grid-drift {
          0% { transform: rotateX(60deg) translateY(0); }
          100% { transform: rotateX(60deg) translateY(60px); }
        }
      `}</style>
    </div>
  );
}
