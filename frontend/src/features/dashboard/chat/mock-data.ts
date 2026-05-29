import {
  DASHBOARD_CHAT_AMBER,
  DASHBOARD_CHAT_AMBER_DIM,
  DASHBOARD_CHAT_ASSISTANT_INTRO,
  DASHBOARD_CHAT_ASSISTANT_REPLY,
  DASHBOARD_CHAT_CYAN,
  DASHBOARD_CHAT_CYAN_DIM,
  DASHBOARD_CHAT_MAGENTA,
  DASHBOARD_CHAT_MAGENTA_DIM,
  DASHBOARD_CHAT_TEAL,
  DASHBOARD_CHAT_TEAL_DIM,
  DASHBOARD_CHAT_USER_FOLLOW_UP,
  DASHBOARD_CHAT_USER_PROMPT,
} from "./constants";
import type { DashboardChatMessage, DashboardConversation } from "./types";

export const MOCK_DASHBOARD_CONVERSATIONS: DashboardConversation[] = [
  {
    id: "1",
    name: "Alter-Ego",
    preview: "The hybrid attention mechanism...",
    time: "2m",
    unread: true,
    avatar: "AE",
    bg: DASHBOARD_CHAT_CYAN_DIM,
    color: DASHBOARD_CHAT_CYAN,
  },
  {
    id: "2",
    name: "Source Knowledge",
    preview: "Looking at the RAG pipeline...",
    time: "1h",
    unread: false,
    avatar: "SK",
    bg: DASHBOARD_CHAT_MAGENTA_DIM,
    color: DASHBOARD_CHAT_MAGENTA,
  },
  {
    id: "3",
    name: "Carousel Preview",
    preview: "Slide 4 needs darker overlay...",
    time: "3h",
    unread: false,
    avatar: "CP",
    bg: DASHBOARD_CHAT_TEAL_DIM,
    color: DASHBOARD_CHAT_TEAL,
  },
  {
    id: "4",
    name: "Content Review",
    preview: "The tone is well-aligned but...",
    time: "1d",
    unread: false,
    avatar: "CT",
    bg: DASHBOARD_CHAT_AMBER_DIM,
    color: DASHBOARD_CHAT_AMBER,
  },
];

export const MOCK_DASHBOARD_MESSAGES: DashboardChatMessage[] = [
  {
    role: "assistant",
    text: DASHBOARD_CHAT_ASSISTANT_INTRO,
    time: "2:15 PM",
  },
  {
    role: "user",
    text: DASHBOARD_CHAT_USER_PROMPT,
    time: "2:16 PM",
  },
  {
    role: "assistant",
    text: DASHBOARD_CHAT_ASSISTANT_REPLY,
    time: "2:17 PM",
  },
  {
    role: "user",
    text: DASHBOARD_CHAT_USER_FOLLOW_UP,
    time: "2:18 PM",
  },
];
