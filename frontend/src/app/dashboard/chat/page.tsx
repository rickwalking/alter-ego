"use client";

import { useState } from "react";
import {
  DASHBOARD_CHAT_BG_CARD,
  DASHBOARD_CHAT_BG_DEEP,
  DASHBOARD_CHAT_BG_ELEVATED,
  DASHBOARD_CHAT_CYAN,
  DASHBOARD_CHAT_CYAN_DIM,
  DASHBOARD_CHAT_MAGENTA,
  DASHBOARD_CHAT_MONO_FONT,
  DASHBOARD_CHAT_TEXT,
  DASHBOARD_CHAT_TEXT_DIM,
  DASHBOARD_CHAT_TEXT_MUTED,
  DASHBOARD_CHAT_TYPING_LABEL,
} from "@/features/dashboard/chat/constants";
import {
  MOCK_DASHBOARD_CONVERSATIONS,
  MOCK_DASHBOARD_MESSAGES,
} from "@/features/dashboard/chat/mock-data";

export default function ChatPage() {
  const [activeConv, setActiveConv] = useState("1");
  const [input, setInput] = useState("");

  return (
    <div
      className="flex flex-col min-h-screen"
      style={{ background: DASHBOARD_CHAT_BG_DEEP }}
    >
      <header
        style={{
          height: "56px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 32px",
          borderBottom: "1px solid rgba(0,212,255,0.06)",
          background: "rgba(6,10,18,0.6)",
          backdropFilter: "blur(12px)",
          WebkitBackdropFilter: "blur(12px)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <h1 style={{ fontSize: "16px", fontWeight: 700 }}>Chat</h1>
          <span
            style={{
              fontFamily: DASHBOARD_CHAT_MONO_FONT,
              fontSize: "11px",
              color: DASHBOARD_CHAT_TEXT_DIM,
            }}
          >
            / <span>Alter-Ego assistant</span>
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <button
            aria-label="Notifications"
            style={{
              position: "relative",
              width: "32px",
              height: "32px",
              borderRadius: "6px",
              background: "transparent",
              border: "1px solid rgba(0,212,255,0.08)",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: DASHBOARD_CHAT_TEXT_MUTED,
            }}
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 0 1-3.46 0" />
            </svg>
            <span
              style={{
                position: "absolute",
                top: "8px",
                right: "8px",
                width: "5px",
                height: "5px",
                borderRadius: "50%",
                background: DASHBOARD_CHAT_MAGENTA,
              }}
            />
          </button>
        </div>
      </header>

      <div
        className="flex flex-1"
        style={{
          height: "calc(100vh - 56px - 240px)",
          minHeight: "calc(100vh - 56px)",
        }}
      >
        <div
          style={{
            width: "280px",
            flexShrink: 0,
            borderRight: "1px solid rgba(0,212,255,0.06)",
            display: "flex",
            flexDirection: "column",
            background: "rgba(6,10,18,0.3)",
          }}
        >
          <div
            style={{
              padding: "16px",
              borderBottom: "1px solid rgba(0,212,255,0.06)",
            }}
          >
            <input
              type="search"
              placeholder="Search conversations..."
              style={{
                width: "100%",
                padding: "8px 12px",
                borderRadius: "6px",
                border: "1px solid rgba(0,212,255,0.08)",
                background: "rgba(0,0,0,0.2)",
                color: DASHBOARD_CHAT_TEXT,
                fontSize: "13px",
                fontFamily: "inherit",
                outline: "none",
              }}
            />
          </div>
          <div style={{ flex: 1, overflowY: "auto", padding: "8px" }}>
            {MOCK_DASHBOARD_CONVERSATIONS.map((conv) => (
              <div
                key={conv.id}
                onClick={() => setActiveConv(conv.id)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  padding: "10px 12px",
                  borderRadius: "6px",
                  cursor: "pointer",
                  background:
                    activeConv === conv.id
                      ? DASHBOARD_CHAT_CYAN_DIM
                      : "transparent",
                  transition: "background 0.2s",
                }}
              >
                <div
                  style={{
                    width: "36px",
                    height: "36px",
                    borderRadius: "50%",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontFamily: DASHBOARD_CHAT_MONO_FONT,
                    fontSize: "12px",
                    fontWeight: 700,
                    flexShrink: 0,
                    background: conv.bg,
                    color: conv.color,
                  }}
                >
                  {conv.avatar}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div
                    style={{
                      fontSize: "13px",
                      fontWeight: 600,
                      color: DASHBOARD_CHAT_TEXT,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {conv.name}
                  </div>
                  <div
                    style={{
                      fontSize: "12px",
                      color: DASHBOARD_CHAT_TEXT_DIM,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                      marginTop: "2px",
                    }}
                  >
                    {conv.preview}
                  </div>
                </div>
                <div
                  style={{
                    fontFamily: DASHBOARD_CHAT_MONO_FONT,
                    fontSize: "10px",
                    color: DASHBOARD_CHAT_TEXT_DIM,
                    flexShrink: 0,
                  }}
                >
                  {conv.time}
                </div>
                {conv.unread && (
                  <div
                    style={{
                      width: "6px",
                      height: "6px",
                      borderRadius: "50%",
                      background: DASHBOARD_CHAT_CYAN,
                      flexShrink: 0,
                    }}
                  />
                )}
              </div>
            ))}
          </div>
        </div>

        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            background: "rgba(6,10,18,0.15)",
          }}
        >
          <div
            style={{
              flex: 1,
              overflowY: "auto",
              padding: "24px",
              display: "flex",
              flexDirection: "column",
              gap: "16px",
            }}
          >
            {MOCK_DASHBOARD_MESSAGES.map((msg, index) => (
              <div
                key={index}
                style={{
                  display: "flex",
                  gap: "10px",
                  maxWidth: "720px",
                  flexDirection: msg.role === "user" ? "row-reverse" : "row",
                  alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
                }}
              >
                {msg.role === "assistant" ? (
                  <div
                    style={{
                      width: "32px",
                      height: "32px",
                      borderRadius: "50%",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontFamily: DASHBOARD_CHAT_MONO_FONT,
                      fontSize: "14px",
                      fontWeight: 700,
                      flexShrink: 0,
                      background: DASHBOARD_CHAT_CYAN_DIM,
                      color: DASHBOARD_CHAT_CYAN,
                    }}
                  >
                    ◆
                  </div>
                ) : (
                  <div
                    style={{
                      width: "32px",
                      height: "32px",
                      borderRadius: "50%",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontFamily: DASHBOARD_CHAT_MONO_FONT,
                      fontSize: "11px",
                      fontWeight: 700,
                      flexShrink: 0,
                      background: DASHBOARD_CHAT_BG_ELEVATED,
                      color: DASHBOARD_CHAT_TEXT_MUTED,
                    }}
                  >
                    PM
                  </div>
                )}
                <div>
                  <div
                    style={{
                      padding: "10px 16px",
                      borderRadius: "10px",
                      fontSize: "13px",
                      lineHeight: 1.65,
                      whiteSpace: "pre-wrap",
                      background:
                        msg.role === "assistant"
                          ? DASHBOARD_CHAT_BG_CARD
                          : DASHBOARD_CHAT_CYAN_DIM,
                      border:
                        msg.role === "assistant"
                          ? "1px solid rgba(255,255,255,0.06)"
                          : "1px solid rgba(0,212,255,0.15)",
                      color:
                        msg.role === "assistant"
                          ? DASHBOARD_CHAT_TEXT_MUTED
                          : DASHBOARD_CHAT_TEXT,
                    }}
                  >
                    {msg.text}
                  </div>
                  <div
                    style={{
                      fontFamily: DASHBOARD_CHAT_MONO_FONT,
                      fontSize: "9px",
                      color: DASHBOARD_CHAT_TEXT_DIM,
                      marginTop: "4px",
                      textAlign: msg.role === "user" ? "right" : "left",
                    }}
                  >
                    {msg.time}
                  </div>
                </div>
              </div>
            ))}
            <div
              style={{
                display: "flex",
                gap: "10px",
                maxWidth: "720px",
                opacity: 0.6,
              }}
            >
              <div
                style={{
                  width: "32px",
                  height: "32px",
                  borderRadius: "50%",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontFamily: DASHBOARD_CHAT_MONO_FONT,
                  fontSize: "14px",
                  fontWeight: 700,
                  flexShrink: 0,
                  background: DASHBOARD_CHAT_CYAN_DIM,
                  color: DASHBOARD_CHAT_CYAN,
                }}
              >
                ◆
              </div>
              <div
                style={{
                  padding: "10px 16px",
                  borderRadius: "10px",
                  fontSize: "13px",
                  background: DASHBOARD_CHAT_BG_CARD,
                  border: "1px solid rgba(255,255,255,0.06)",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                }}
              >
                <span
                  style={{
                    display: "inline-block",
                    width: "6px",
                    height: "6px",
                    borderRadius: "50%",
                    background: DASHBOARD_CHAT_CYAN,
                  }}
                />
                {DASHBOARD_CHAT_TYPING_LABEL}
              </div>
            </div>
          </div>

          <div
            style={{
              padding: "16px 24px",
              borderTop: "1px solid rgba(0,212,255,0.06)",
              background: "rgba(6,10,18,0.4)",
            }}
          >
            <div
              style={{ display: "flex", gap: "10px", alignItems: "flex-end" }}
            >
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask the Alter-Ego anything..."
                rows={1}
                style={{
                  flex: 1,
                  padding: "10px 16px",
                  borderRadius: "8px",
                  border: "1px solid rgba(0,212,255,0.1)",
                  background: "rgba(0,0,0,0.25)",
                  color: DASHBOARD_CHAT_TEXT,
                  fontSize: "13px",
                  fontFamily: "inherit",
                  lineHeight: 1.5,
                  resize: "none",
                  minHeight: "42px",
                  maxHeight: "120px",
                  outline: "none",
                }}
              />
              <button
                aria-label="Send message"
                style={{
                  width: "42px",
                  height: "42px",
                  borderRadius: "8px",
                  border: "none",
                  background: DASHBOARD_CHAT_CYAN,
                  color: DASHBOARD_CHAT_BG_DEEP,
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                }}
              >
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke={DASHBOARD_CHAT_BG_DEEP}
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <line x1="22" y1="2" x2="11" y2="13" />
                  <polygon points="22 2 15 22 11 13 2 9 22 2" />
                </svg>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
