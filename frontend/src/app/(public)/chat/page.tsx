import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { PublicChatView } from "@/app/(public)/chat/public-chat-view";
import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";
import { COOKIE_ACCESS_TOKEN, isLiveSession } from "@/modules/identity";

/**
 * Visitors chat here without history; a signed-in user is sent to the
 * dashboard chat, where their conversations are kept.
 */
export default async function PublicChatPage(): Promise<React.ReactElement> {
  const token = (await cookies()).get(COOKIE_ACCESS_TOKEN)?.value;
  if (await isLiveSession(token)) {
    redirect(DASHBOARD_ROUTES.CHAT);
  }
  return <PublicChatView />;
}
