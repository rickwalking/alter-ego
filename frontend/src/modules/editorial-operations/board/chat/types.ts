export type DashboardChatRole = "assistant" | "user";

export interface DashboardConversation {
  id: string;
  name: string;
  time: string;
}

export interface DashboardChatMessage {
  role: DashboardChatRole;
  text: string;
  time: string;
}
