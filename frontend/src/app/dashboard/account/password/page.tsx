"use client";

import { useTranslations } from "next-intl";
import { ChangePasswordForm } from "@/components/account/change-password-form";
import { NeonTopBar } from "@/components/organisms/neon-top-bar";
import { DASHBOARD_PAGE_FONT_FAMILY } from "@/constants/dashboard-page";
import { useAuth, useChangePassword } from "@/modules/identity";

/**
 * Change my own password. A user whose password an admin reset lands here and
 * stays here until they change it (the app shell gate and the API enforce it).
 */
export default function ChangePasswordPage(): React.ReactElement {
  const t = useTranslations("account.password");
  const { user } = useAuth();
  const forced = user?.must_change_password === true;
  const controller = useChangePassword(forced);
  return (
    <div
      className="flex-1 text-white relative"
      style={{ fontFamily: DASHBOARD_PAGE_FONT_FAMILY }}
    >
      <NeonTopBar title={t("title")} breadcrumb={[{ label: t("title") }]} />
      <div className="mx-auto w-full max-w-[480px] p-6">
        <ChangePasswordForm controller={controller} forced={forced} />
      </div>
    </div>
  );
}
