export type DashboardChatRole = "assistant" | "user";

export interface DashboardConversation {
  id: string;
  name: string;
  preview: string;
  time: string;
  unread: boolean;
  avatar: string;
  bg: string;
  color: string;
}

export interface DashboardChatMessage {
  role: DashboardChatRole;
  text: string;
  time: string;
}
