"use client";

import { useEffect, useMemo, useState } from "react";
import {
  useConversationPages,
  useConversationSearch,
} from "@/modules/conversation";
import { mapConversationToDashboard } from "@/modules/editorial-operations";
import type { DashboardConversation } from "@/modules/editorial-operations";
import type { Conversation } from "@/schemas/chat";
import { filterConversations } from "./chat-sidebar-filter";

/** How long typing pauses before the server is asked to search. */
export const SIDEBAR_SEARCH_DEBOUNCE_MS = 300;

export interface SidebarConversations {
  /** Every conversation loaded so far, newest first. */
  loaded: Conversation[];
  refetch: () => unknown;
  /** What the sidebar lists, and how it searches and pages. */
  sidebar: {
    conversations: DashboardConversation[];
    query: string;
    onQueryChange: (query: string) => void;
    searching: boolean;
    hasMore: boolean;
    onLoadMore: () => void;
  };
}

/** ``query`` once it has stopped changing for the debounce delay. */
function useSettled(query: string): string {
  const [settled, setSettled] = useState(query);
  useEffect(() => {
    const timer = setTimeout(() => {
      setSettled(query);
    }, SIDEBAR_SEARCH_DEBOUNCE_MS);
    return () => {
      clearTimeout(timer);
    };
  }, [query]);
  return settled;
}

/** The loaded matches first, then server matches from older pages, no repeats. */
function mergeMatches(
  local: DashboardConversation[],
  remote: DashboardConversation[],
): DashboardConversation[] {
  const seen = new Set(local.map((conv) => conv.id));
  return [...local, ...remote.filter((conv) => !seen.has(conv.id))];
}

/**
 * The dashboard sidebar's conversations: loaded a page at a time, and while a
 * search is typed, the loaded ones that match (case and accents ignored) plus
 * the server's title matches from every page, so older chats are found too.
 */
export function useSidebarConversations(
  locale: string,
  untitled: string,
): SidebarConversations {
  const pages = useConversationPages();
  const [query, setQuery] = useState("");
  const term = useSettled(query.trim());
  const search = useConversationSearch(term);
  const loaded = useMemo(
    () => pages.data?.pages.flatMap((page) => page.items) ?? [],
    [pages.data],
  );
  const conversations = useMemo(() => {
    const toSidebar = (conversation: Conversation) =>
      mapConversationToDashboard(conversation, locale, untitled);
    const local = filterConversations(loaded.map(toSidebar), query);
    if (!query.trim()) return local;
    return mergeMatches(local, (search.data ?? []).map(toSidebar));
  }, [loaded, query, search.data, locale, untitled]);
  const searching =
    query.trim() !== "" && (term !== query.trim() || search.isFetching);
  return {
    loaded,
    refetch: pages.refetch,
    sidebar: {
      conversations,
      query,
      onQueryChange: setQuery,
      searching,
      hasMore: pages.hasNextPage && !query.trim(),
      onLoadMore: () => void pages.fetchNextPage(),
    },
  };
}
