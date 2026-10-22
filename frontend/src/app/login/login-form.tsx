import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonInput } from "@/components/atoms/neon-input";
import { NeonFormField } from "@/components/molecules/neon-form-field";
import { BG_CARD } from "@/constants/neon";
import type { LoginController } from "./use-login";

export function LoginForm({
  email,
  password,
  error,
  isLoading,
  setEmail,
  setPassword,
  handleSubmit,
}: Readonly<LoginController>) {
  const t = useTranslations("auth");
  return (
    <form
      onSubmit={(e) => {
        void handleSubmit(e);
      }}
      style={{
        background: BG_CARD,
        border: "1px solid rgba(255,255,255,0.06)",
        borderRadius: "8px",
        padding: "32px",
      }}
    >
      {error && (
        <div
          style={{
            marginBottom: "20px",
            padding: "10px 14px",
            borderRadius: "6px",
            fontSize: "13px",
            background: "rgba(239,68,68,0.12)",
            color: "#ef4444",
            border: "1px solid rgba(239,68,68,0.15)",
          }}
        >
          {error}
        </div>
      )}

      <NeonFormField label={t("emailLabel")} name="email" required>
        <NeonInput
          id="email"
          name="email"
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder={t("emailPlaceholder")}
        />
      </NeonFormField>

      <NeonFormField
        label={t("passwordLabel")}
        name="password"
        required
        className="mb-6"
      >
        <NeonInput
          id="password"
          name="password"
          type="password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder={t("passwordPlaceholder")}
        />
      </NeonFormField>

      <NeonButton
        type="submit"
        fullWidth
        loading={isLoading}
        disabled={isLoading}
      >
        {isLoading ? t("signingIn") : t("signIn")}
      </NeonButton>
    </form>
  );
}
