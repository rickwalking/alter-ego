"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";
import { useAuth } from "@/modules/identity";

/**
 * Keeps a user with an admin-issued temporary password on the change-password
 * page: any other dashboard or admin page is replaced by a redirect and its
 * content is not rendered. The API refuses those users too (403
 * `password_change_required`); this only spares them a page of errors.
 */
export function PasswordChangeGate({
  children,
}: Readonly<{ children: React.ReactNode }>): React.ReactElement | null {
  const { user } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const blocked =
    user?.must_change_password === true &&
    pathname !== DASHBOARD_ROUTES.ACCOUNT_PASSWORD;

  useEffect(() => {
    if (blocked) {
      router.replace(DASHBOARD_ROUTES.ACCOUNT_PASSWORD);
    }
  }, [blocked, router]);

  if (blocked) {
    return null;
  }
  return <>{children}</>;
}
