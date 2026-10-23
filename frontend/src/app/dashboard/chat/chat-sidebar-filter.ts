import type { DashboardConversation } from "@/modules/editorial-operations";

/** Case- and accent-insensitive form used to match a search query. */
function searchable(text: string): string {
  return text
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLocaleLowerCase();
}

/** The conversations whose title contains the query (all when it is blank). */
export function filterConversations(
  conversations: DashboardConversation[],
  query: string,
): DashboardConversation[] {
  const needle = searchable(query.trim());
  if (!needle) return conversations;
  return conversations.filter((conv) => searchable(conv.name).includes(needle));
}
