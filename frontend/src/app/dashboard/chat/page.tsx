"use client";

import { useState } from "react";

const CYAN = "#00d4ff";
const CYAN_DIM = "rgba(0,212,255,0.12)";
const MAGENTA = "#ff2770";
const MAGENTA_DIM = "rgba(255,39,112,0.12)";
const TEAL = "#0ac5a8";
const TEAL_DIM = "rgba(10,197,168,0.12)";
const AMBER = "#f59e0b";
const AMBER_DIM = "rgba(245,158,11,0.12)";
const BG_DEEP = "#060a12";
const BG_CARD = "#0d1324";
const BG_ELEVATED = "#111a30";
const TEXT = "rgba(255,255,255,0.88)";
const TEXT_MUTED = "rgba(255,255,255,0.55)";
const TEXT_DIM = "rgba(255,255,255,0.3)";

const CONVERSATIONS = [
  {
    id: "1",
    name: "Alter-Ego",
    preview: "The hybrid attention mechanism...",
    time: "2m",
    unread: true,
    avatar: "AE",
    bg: CYAN_DIM,
    color: CYAN,
  },
  {
    id: "2",
    name: "Source Knowledge",
    preview: "Looking at the RAG pipeline...",
    time: "1h",
    unread: false,
    avatar: "SK",
    bg: MAGENTA_DIM,
    color: MAGENTA,
  },
  {
    id: "3",
    name: "Carousel Preview",
    preview: "Slide 4 needs darker overlay...",
    time: "3h",
    unread: false,
    avatar: "CP",
    bg: TEAL_DIM,
    color: TEAL,
  },
  {
    id: "4",
    name: "Content Review",
    preview: "The tone is well-aligned but...",
    time: "1d",
    unread: false,
    avatar: "CT",
    bg: AMBER_DIM,
    color: AMBER,
  },
];

const MESSAGES = [
  {
    role: "assistant",
    text: "Hello Pedro. I'm your Alter-Ego assistant. I have access to your knowledge graph, carousel pipeline, and blog archive. How can I help you today?",
    time: "2:15 PM",
  },
  {
    role: "user",
    text: "Can you review the DeepSeek V4 carousel draft and check if the market positioning aligns with the competitive analysis we did last week?",
    time: "2:16 PM",
  },
  {
    role: "assistant",
    text: "I've cross-referenced the carousel with the competitive analysis from last week. A few observations:\n\n1. The price comparison slide ($3.50 vs $25) is accurate and well-contextualized.\n2. The benchmark data (93.5% LiveCodeBench) matches our latest evaluation run.\n3. Consider adding a note about the Huawei Ascend chip compatibility, which was a key differentiator in our analysis.",
    time: "2:17 PM",
  },
  {
    role: "user",
    text: "Good catch. I'll add the Huawei chip detail. Can you also check the tone for the technical audience slide?",
    time: "2:18 PM",
  },
];

export default function ChatPage() {
  const [activeConv, setActiveConv] = useState("1");
  const [input, setInput] = useState("");

  return (
    <div className="flex flex-col min-h-screen" style={{ background: BG_DEEP }}>
      {/* Top Bar */}
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
              fontFamily: "'JetBrains Mono', ui-monospace, monospace",
              fontSize: "11px",
              color: TEXT_DIM,
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
              color: TEXT_MUTED,
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
                background: MAGENTA,
              }}
            />
          </button>
        </div>
      </header>

      {/* Chat Layout */}
      <div
        className="flex flex-1"
        style={{
          height: "calc(100vh - 56px - 240px)",
          minHeight: "calc(100vh - 56px)",
        }}
      >
        {/* Chat Sidebar */}
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
                color: TEXT,
                fontSize: "13px",
                fontFamily: "inherit",
                outline: "none",
              }}
            />
          </div>
          <div style={{ flex: 1, overflowY: "auto", padding: "8px" }}>
            {CONVERSATIONS.map((conv) => (
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
                  background: activeConv === conv.id ? CYAN_DIM : "transparent",
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
                    fontFamily: "'JetBrains Mono', ui-monospace, monospace",
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
                      color: TEXT,
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
                      color: TEXT_DIM,
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
                    fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                    fontSize: "10px",
                    color: TEXT_DIM,
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
                      background: CYAN,
                      flexShrink: 0,
                    }}
                  />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Chat Main */}
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
            {MESSAGES.map((msg, i) => (
              <div
                key={i}
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
                      fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                      fontSize: "14px",
                      fontWeight: 700,
                      flexShrink: 0,
                      background: CYAN_DIM,
                      color: CYAN,
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
                      fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                      fontSize: "11px",
                      fontWeight: 700,
                      flexShrink: 0,
                      background: BG_ELEVATED,
                      color: TEXT_MUTED,
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
                      background: msg.role === "assistant" ? BG_CARD : CYAN_DIM,
                      border:
                        msg.role === "assistant"
                          ? "1px solid rgba(255,255,255,0.06)"
                          : "1px solid rgba(0,212,255,0.15)",
                      color: msg.role === "assistant" ? TEXT_MUTED : TEXT,
                    }}
                  >
                    {msg.text}
                  </div>
                  <div
                    style={{
                      fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                      fontSize: "9px",
                      color: TEXT_DIM,
                      marginTop: "4px",
                      textAlign: msg.role === "user" ? "right" : "left",
                    }}
                  >
                    {msg.time}
                  </div>
                </div>
              </div>
            ))}
            {/* Typing indicator */}
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
                  fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                  fontSize: "14px",
                  fontWeight: 700,
                  flexShrink: 0,
                  background: CYAN_DIM,
                  color: CYAN,
                }}
              >
                ◆
              </div>
              <div
                style={{
                  padding: "10px 16px",
                  borderRadius: "10px",
                  fontSize: "13px",
                  background: BG_CARD,
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
                    background: CYAN,
                  }}
                />
                Analyzing tone alignment...
              </div>
            </div>
          </div>

          {/* Input Area */}
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
                  border: `1px solid rgba(0,212,255,0.1)`,
                  background: "rgba(0,0,0,0.25)",
                  color: TEXT,
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
                  background: CYAN,
                  color: BG_DEEP,
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
                  stroke={BG_DEEP}
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
