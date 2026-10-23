import { PublicChatView } from "@/app/(public)/chat/public-chat-view";
import { redirectSignedInToDashboardChat } from "@/app/(public)/chat/redirect-signed-in";

/**
 * Visitors chat here without history; a signed-in user is sent to the
 * dashboard chat, where their conversations are kept.
 */
export default async function PublicChatPage(): Promise<React.ReactElement> {
  await redirectSignedInToDashboardChat();
  return <PublicChatView />;
}
