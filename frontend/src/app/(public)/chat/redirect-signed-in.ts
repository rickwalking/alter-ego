import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";
import { COOKIE_ACCESS_TOKEN, isLiveSession } from "@/modules/identity";

/**
 * Sends a signed-in user to the dashboard chat, where their conversations are
 * kept; a visitor or an expired session stays on the public chat.
 */
export async function redirectSignedInToDashboardChat(): Promise<void> {
  const token = (await cookies()).get(COOKIE_ACCESS_TOKEN)?.value;
  if (await isLiveSession(token)) {
    redirect(DASHBOARD_ROUTES.CHAT);
  }
}
