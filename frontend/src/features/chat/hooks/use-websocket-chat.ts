import { useEffect, useRef, useState, useCallback } from "react";
import { type Message, type MessageSource } from "@/schemas/chat";

interface WebSocketEvent {
  type: "token" | "sources" | "complete" | "error";
  content?: string;
  sources?: MessageSource[];
}

interface UseWebSocketChatOptions {
  conversationId: string | null;
  baseUrl?: string;
  fallbackToSse?: boolean;
}

interface UseWebSocketChatReturn {
  messages: Message[];
  isConnected: boolean;
  isStreaming: boolean;
  sendMessage: (content: string) => void;
  error: string | null;
}

export function useWebSocketChat({
  conversationId,
  baseUrl = "",
  fallbackToSse = true,
}: UseWebSocketChatOptions): UseWebSocketChatReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const streamingContentRef = useRef("");
  const streamingMsgIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (!conversationId) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = baseUrl
      ? baseUrl.replace(/^http/, "ws") + `/ws/chat/${conversationId}`
      : `${protocol}//${window.location.host}/ws/chat/${conversationId}`;

    const socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      setIsConnected(true);
      setError(null);
    };

    socket.onclose = () => {
      setIsConnected(false);
      setIsStreaming(false);
    };

    socket.onmessage = (event) => {
      try {
        const data: WebSocketEvent = JSON.parse(event.data);

        switch (data.type) {
          case "token": {
            streamingContentRef.current += data.content || "";
            setMessages((prev) => {
              const last = prev[prev.length - 1];
              if (last?.role === "assistant" && last.id === streamingMsgIdRef.current) {
                return [
                  ...prev.slice(0, -1),
                  { ...last, content: streamingContentRef.current },
                ];
              }
              const newMsg: Message = {
                id: streamingMsgIdRef.current || `stream-${Date.now()}`,
                role: "assistant",
                content: streamingContentRef.current,
                sources: [],
                created_at: new Date().toISOString(),
              };
              if (!streamingMsgIdRef.current) {
                streamingMsgIdRef.current = newMsg.id;
              }
              return [...prev, newMsg];
            });
            break;
          }

          case "sources": {
            const sources = data.sources || [];
            setMessages((prev) => {
              const last = prev[prev.length - 1];
              if (last?.role === "assistant") {
                return [...prev.slice(0, -1), { ...last, sources }];
              }
              return prev;
            });
            break;
          }

          case "complete": {
            setIsStreaming(false);
            streamingContentRef.current = "";
            streamingMsgIdRef.current = null;
            break;
          }

          case "error": {
            setError(data.content || "Unknown error");
            setIsStreaming(false);
            streamingContentRef.current = "";
            streamingMsgIdRef.current = null;
            break;
          }
        }
      } catch {
        // Ignore parse errors
      }
    };

    socket.onerror = () => {
      setError("WebSocket connection failed");
      setIsConnected(false);
    };

    wsRef.current = socket;

    return () => {
      socket.close();
      wsRef.current = null;
    };
  }, [conversationId, baseUrl]);

  const sendMessage = useCallback(
    (content: string) => {
      if (!content.trim()) return;

      const userMsg: Message = {
        id: `user-${Date.now()}`,
        role: "user",
        content: content.trim(),
        sources: [],
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);

      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ content: content.trim() }));
        setIsStreaming(true);
        streamingMsgIdRef.current = null;
        streamingContentRef.current = "";
      } else if (fallbackToSse && conversationId) {
        // Fallback to SSE streaming
        fetchSseResponse(content.trim(), conversationId);
      }
    },
    [conversationId, fallbackToSse]
  );

  const fetchSseResponse = useCallback(async (content: string, convId: string) => {
    setIsStreaming(true);
    try {
      const response = await fetch(`/api/conversations/${convId}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
      });

      if (!response.ok) throw new Error("API request failed");

      const data = await response.json();
      const assistantMsg: Message = {
        id: `sse-${Date.now()}`,
        role: "assistant",
        content: data.content || "",
        sources: data.sources || [],
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to get response");
    } finally {
      setIsStreaming(false);
    }
  }, []);

  return { messages, isConnected, isStreaming, sendMessage, error };
}
