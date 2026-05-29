"use client";

import { useState } from "react";

const CYAN = "#00d4ff";
const CYAN_DIM = "rgba(0,212,255,0.12)";
const TEXT = "rgba(255,255,255,0.88)";
const TEXT_MUTED = "rgba(255,255,255,0.55)";
const TEXT_DIM = "rgba(255,255,255,0.3)";

const STEPS = [
  { num: 1, label: "Brief" },
  { num: 2, label: "Research" },
  { num: 3, label: "Outline" },
  { num: 4, label: "Content" },
  { num: 5, label: "Images" },
  { num: 6, label: "Review" },
  { num: 7, label: "Publish" },
];

const TEMPLATES = [
  { icon: "📊", name: "Analysis", desc: "Deep dive with data" },
  { icon: "⚖️", name: "Comparison", desc: "Side by side" },
  { icon: "📚", name: "Tutorial", desc: "Step by step" },
  { icon: "📰", name: "News Flash", desc: "Quick update" },
  { icon: "🧠", name: "Deep Dive", desc: "Comprehensive" },
  { icon: "🎯", name: "Listicle", desc: "Top N format" },
];

const ARTIFACTS = [
  {
    name: "Research Report",
    desc: "Collecting data from Twitter, GitHub, tech blogs, and documentation...",
    status: "pending",
  },
  {
    name: "Slide Outline",
    desc: "Generating structured outline with slide-by-slide breakdown...",
    status: "pending",
  },
  {
    name: "Slide Content",
    desc: "Drafting content with persona voice matching...",
    status: "pending",
  },
  {
    name: "Design Tokens",
    desc: "Generating color palette, typography, and layout tokens...",
    status: "pending",
  },
  {
    name: "Generated Images",
    desc: "Creating custom images with selected model and style...",
    status: "pending",
  },
  {
    name: "Final Review",
    desc: "Quality check, persona enforcement, and rubric validation...",
    status: "pending",
  },
];

export default function CreateCarouselPage() {
  const [selectedTemplate, setSelectedTemplate] = useState(0);

  return (
    <div
      className="flex-1 text-white relative"
      style={{ fontFamily: "Inter, system-ui, sans-serif" }}
    >
      {/* Top Bar */}
      <div className="h-[56px] flex items-center justify-between px-6 border-b border-[rgba(0,212,255,0.06)] bg-[rgba(6,10,18,0.6)] backdrop-blur-xl sticky top-0 z-30">
        <div className="flex items-center gap-3">
          <h1 className="text-[16px] font-bold">Create Carousel</h1>
          <div className="font-mono text-[11px] text-[rgba(255,255,255,0.3)]">
            / <span>new project</span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <input
            type="search"
            style={{
              padding: "6px 12px",
              borderRadius: "4px",
              background: "rgba(0,0,0,0.2)",
              border: "1px solid rgba(0,212,255,0.08)",
              color: "rgba(255,255,255,0.55)",
              fontSize: "13px",
              width: "200px",
              outline: "none",
              fontFamily: "'JetBrains Mono', ui-monospace, monospace",
            }}
            placeholder="Search..."
          />
          <button
            aria-label="Notifications"
            style={{
              width: "32px",
              height: "32px",
              borderRadius: "4px",
              border: "none",
              background: "transparent",
              color: TEXT_MUTED,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              position: "relative",
            }}
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            >
              <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
              <path d="M13.73 21a2 2 0 0 1-3.46 0" />
            </svg>
            <span
              style={{
                position: "absolute",
                top: "6px",
                right: "6px",
                width: "6px",
                height: "6px",
                borderRadius: "50%",
                background: "#ff2770",
              }}
            />
          </button>
        </div>
      </div>

      <div className="p-7">
        {/* Progress Steps */}
        <div
          style={{
            display: "flex",
            marginBottom: "28px",
            background: "#0d1324",
            borderRadius: "8px",
            border: "1px solid rgba(255,255,255,0.06)",
            overflow: "hidden",
          }}
        >
          {STEPS.map((step) => (
            <div
              key={step.num}
              style={{
                flex: 1,
                padding: "12px 16px",
                display: "flex",
                alignItems: "center",
                gap: "8px",
                fontSize: "12px",
                color: step.num === 1 ? TEXT : TEXT_DIM,
                borderRight:
                  step.num < STEPS.length
                    ? "1px solid rgba(255,255,255,0.04)"
                    : "none",
              }}
            >
              <span
                style={{
                  width: "20px",
                  height: "20px",
                  borderRadius: "50%",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                  fontSize: "10px",
                  fontWeight: 700,
                  flexShrink: 0,
                  background:
                    step.num === 1 ? CYAN_DIM : "rgba(255,255,255,0.04)",
                  color: step.num === 1 ? CYAN : TEXT_DIM,
                }}
              >
                {step.num}
              </span>
              <span>{step.label}</span>
            </div>
          ))}
        </div>

        {/* Main Layout */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 360px",
            gap: "24px",
          }}
        >
          {/* Left Column - Forms */}
          <div
            style={{ display: "flex", flexDirection: "column", gap: "24px" }}
          >
            {/* Section 1: Topic & Brief */}
            <div
              style={{
                background: "#0d1324",
                border: "1px solid rgba(255,255,255,0.06)",
                borderRadius: "8px",
                padding: "24px",
              }}
            >
              <div
                style={{
                  fontSize: "14px",
                  fontWeight: 700,
                  marginBottom: "12px",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                }}
              >
                <span
                  style={{
                    width: "22px",
                    height: "22px",
                    borderRadius: "50%",
                    background: CYAN_DIM,
                    color: CYAN,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                    fontSize: "11px",
                    fontWeight: 700,
                  }}
                >
                  1
                </span>
                Topic & Brief
              </div>
              <div style={{ marginBottom: "14px" }}>
                <label
                  style={{
                    fontSize: "12px",
                    color: TEXT_MUTED,
                    marginBottom: "6px",
                    display: "block",
                  }}
                >
                  Carousel Topic{" "}
                  <span style={{ color: TEXT_DIM, fontSize: "11px" }}>
                    (max 500 chars)
                  </span>
                </label>
                <input
                  type="text"
                  defaultValue="DeepSeek V4 Analysis"
                  style={{
                    width: "100%",
                    padding: "10px 12px",
                    borderRadius: "6px",
                    border: "1px solid rgba(255,255,255,0.08)",
                    background: "rgba(6,10,18,0.6)",
                    color: TEXT,
                    fontSize: "13px",
                    outline: "none",
                  }}
                  placeholder="e.g., DeepSeek V4: Open-Source LLM Benchmark Performance"
                />
              </div>
              <div style={{ marginBottom: "14px" }}>
                <label
                  style={{
                    fontSize: "12px",
                    color: TEXT_MUTED,
                    marginBottom: "6px",
                    display: "block",
                  }}
                >
                  Target Audience{" "}
                  <span style={{ color: TEXT_DIM, fontSize: "11px" }}>
                    (max 500 chars)
                  </span>
                </label>
                <input
                  type="text"
                  defaultValue="AI/ML Engineers, Software Developers"
                  style={{
                    width: "100%",
                    padding: "10px 12px",
                    borderRadius: "6px",
                    border: "1px solid rgba(255,255,255,0.08)",
                    background: "rgba(6,10,18,0.6)",
                    color: TEXT,
                    fontSize: "13px",
                    outline: "none",
                  }}
                  placeholder="Who should read this carousel?"
                />
              </div>
              <div>
                <label
                  style={{
                    fontSize: "12px",
                    color: TEXT_MUTED,
                    marginBottom: "6px",
                    display: "block",
                  }}
                >
                  Brief / Description{" "}
                  <span style={{ color: TEXT_DIM, fontSize: "11px" }}>
                    (max 200 chars)
                  </span>
                </label>
                <textarea
                  defaultValue="Analyze DeepSeek V4's architecture, benchmark performance against open-source LLMs, pricing strategy, and implications for the open-source AI landscape."
                  rows={4}
                  style={{
                    width: "100%",
                    padding: "10px 12px",
                    borderRadius: "6px",
                    border: "1px solid rgba(255,255,255,0.08)",
                    background: "rgba(6,10,18,0.6)",
                    color: TEXT,
                    fontSize: "13px",
                    outline: "none",
                    resize: "vertical",
                    fontFamily: "inherit",
                  }}
                  placeholder="What should this carousel cover?"
                />
              </div>
            </div>

            {/* Section 2: Template Style */}
            <div
              style={{
                background: "#0d1324",
                border: "1px solid rgba(255,255,255,0.06)",
                borderRadius: "8px",
                padding: "24px",
              }}
            >
              <div
                style={{
                  fontSize: "14px",
                  fontWeight: 700,
                  marginBottom: "12px",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                }}
              >
                <span
                  style={{
                    width: "22px",
                    height: "22px",
                    borderRadius: "50%",
                    background: CYAN_DIM,
                    color: CYAN,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                    fontSize: "11px",
                    fontWeight: 700,
                  }}
                >
                  2
                </span>
                Template Style
              </div>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(3, 1fr)",
                  gap: "10px",
                }}
              >
                {TEMPLATES.map((tpl, idx) => (
                  <div
                    key={tpl.name}
                    onClick={() => setSelectedTemplate(idx)}
                    style={{
                      background:
                        idx === selectedTemplate ? CYAN_DIM : "#0d1324",
                      border:
                        idx === selectedTemplate
                          ? `1px solid ${CYAN}`
                          : "1px solid rgba(255,255,255,0.06)",
                      borderRadius: "8px",
                      padding: "14px",
                      cursor: "pointer",
                      transition: "all 0.2s",
                      textAlign: "center",
                    }}
                  >
                    <div style={{ fontSize: "20px", marginBottom: "4px" }}>
                      {tpl.icon}
                    </div>
                    <h4
                      style={{
                        fontSize: "12px",
                        fontWeight: 600,
                        color: TEXT,
                        margin: 0,
                      }}
                    >
                      {tpl.name}
                    </h4>
                    <p
                      style={{
                        fontSize: "10px",
                        color: TEXT_DIM,
                        margin: "4px 0 0",
                      }}
                    >
                      {tpl.desc}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* Section 3: Theme & Voice */}
            <div
              style={{
                background: "#0d1324",
                border: "1px solid rgba(255,255,255,0.06)",
                borderRadius: "8px",
                padding: "24px",
              }}
            >
              <div
                style={{
                  fontSize: "14px",
                  fontWeight: 700,
                  marginBottom: "12px",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                }}
              >
                <span
                  style={{
                    width: "22px",
                    height: "22px",
                    borderRadius: "50%",
                    background: CYAN_DIM,
                    color: CYAN,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                    fontSize: "11px",
                    fontWeight: 700,
                  }}
                >
                  3
                </span>
                Theme & Voice
              </div>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "12px",
                }}
              >
                <div>
                  <label
                    style={{
                      fontSize: "12px",
                      color: TEXT_MUTED,
                      marginBottom: "6px",
                      display: "block",
                    }}
                  >
                    Theme{" "}
                    <span style={{ color: TEXT_DIM, fontSize: "11px" }}>
                      (enum)
                    </span>
                  </label>
                  <select
                    style={{
                      width: "100%",
                      padding: "10px 12px",
                      borderRadius: "6px",
                      border: "1px solid rgba(255,255,255,0.08)",
                      background: "rgba(6,10,18,0.45)",
                      color: TEXT,
                      fontSize: "13px",
                      outline: "none",
                    }}
                  >
                    <option value="auto">Auto-detect</option>
                    <option value="cybersecurity">Cybersecurity</option>
                    <option value="ai_competition">AI Competition</option>
                    <option value="developer_skills">Developer Skills</option>
                    <option value="source_code">Source Code</option>
                    <option value="social_engineering">
                      Social Engineering
                    </option>
                  </select>
                </div>
                <div>
                  <label
                    style={{
                      fontSize: "12px",
                      color: TEXT_MUTED,
                      marginBottom: "6px",
                      display: "block",
                    }}
                  >
                    Image Preset{" "}
                    <span style={{ color: TEXT_DIM, fontSize: "11px" }}>
                      (model + style)
                    </span>
                  </label>
                  <select
                    style={{
                      width: "100%",
                      padding: "10px 12px",
                      borderRadius: "6px",
                      border: "1px solid rgba(255,255,255,0.08)",
                      background: "rgba(6,10,18,0.45)",
                      color: TEXT,
                      fontSize: "13px",
                      outline: "none",
                    }}
                  >
                    <option value="default">Default (SDXL + realistic)</option>
                    <option value="cyberpunk">Cyberpunk</option>
                    <option value="minimal">Minimal</option>
                    <option value="tech">Tech</option>
                  </select>
                </div>
              </div>
            </div>
          </div>

          {/* Right Sidebar */}
          <div
            style={{
              position: "sticky",
              top: "84px",
              alignSelf: "start",
              display: "flex",
              flexDirection: "column",
              gap: "16px",
            }}
          >
            <div
              style={{
                background: "#0d1324",
                border: "1px solid rgba(255,255,255,0.06)",
                borderRadius: "8px",
                padding: "20px",
              }}
            >
              <h3
                style={{
                  fontSize: "14px",
                  fontWeight: 700,
                  marginBottom: "12px",
                }}
              >
                Project Summary
              </h3>
              {[
                { label: "Type", value: "Analysis" },
                {
                  label: "Slides",
                  value: "1 intro, 3 content, 1 closing, 1 CTA",
                },
                { label: "Aspect Ratio", value: "1080x1350" },
                { label: "Language", value: "pt-BR" },
                { label: "Generate Images", value: "Yes" },
                { label: "Status", value: "Draft", badge: true },
              ].map((row) => (
                <div
                  key={row.label}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    padding: "8px 0",
                    fontSize: "13px",
                    borderBottom: "1px solid rgba(255,255,255,0.03)",
                  }}
                >
                  <span style={{ color: TEXT_DIM }}>{row.label}</span>
                  {row.badge ? (
                    <span
                      style={{
                        padding: "2px 6px",
                        borderRadius: "4px",
                        fontSize: "11px",
                        fontWeight: 600,
                        background: "rgba(245,158,11,0.15)",
                        color: "#f59e0b",
                      }}
                    >
                      {row.value}
                    </span>
                  ) : (
                    <span style={{ color: TEXT, fontWeight: 600 }}>
                      {row.value}
                    </span>
                  )}
                </div>
              ))}
            </div>

            <div
              style={{
                background: "#0d1324",
                border: "1px solid rgba(255,255,255,0.06)",
                borderRadius: "8px",
                padding: "20px",
              }}
            >
              <h3
                style={{
                  fontSize: "14px",
                  fontWeight: 700,
                  marginBottom: "12px",
                }}
              >
                Generation Report
              </h3>
              <div style={{ maxHeight: "400px", overflowY: "auto" }}>
                {ARTIFACTS.map((artifact) => (
                  <div
                    key={artifact.name}
                    style={{
                      padding: "12px 0",
                      borderBottom: "1px solid rgba(255,255,255,0.04)",
                    }}
                  >
                    <h4
                      style={{
                        fontSize: "12px",
                        fontWeight: 600,
                        color: TEXT,
                        margin: "0 0 4px",
                      }}
                    >
                      {artifact.name}
                    </h4>
                    <p
                      style={{
                        fontSize: "10px",
                        color: TEXT_DIM,
                        margin: 0,
                        lineHeight: 1.4,
                      }}
                    >
                      {artifact.desc}
                    </p>
                    <span
                      style={{
                        display: "inline-block",
                        fontSize: "9px",
                        padding: "1px 6px",
                        borderRadius: "3px",
                        fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                        marginTop: "6px",
                        background: "rgba(255,165,0,0.15)",
                        color: "#ffa500",
                      }}
                    >
                      {artifact.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <button
              style={{
                width: "100%",
                padding: "12px",
                borderRadius: "6px",
                border: "none",
                background: "linear-gradient(135deg, #00d4ff 0%, #0090b0 100%)",
                color: "#060a12",
                fontSize: "13px",
                fontWeight: 700,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "8px",
                fontFamily: "inherit",
              }}
            >
              Start Carousel
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
