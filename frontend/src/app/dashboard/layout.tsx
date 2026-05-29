"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";

const CYAN = "#00d4ff";
const CYAN_DIM = "rgba(0,212,255,0.12)";
const BG_SIDEBAR = "#080c18";
const TEXT = "rgba(255,255,255,0.88)";
const TEXT_MUTED = "rgba(255,255,255,0.55)";
const TEXT_DIM = "rgba(255,255,255,0.3)";

const SIDEBAR_SECTIONS = [
  {
    sectionKey: "sectionMain",
    items: [
      {
        href: "/dashboard",
        labelKey: "dashboard",
        icon: "M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z",
      },
      {
        href: "/dashboard/chat",
        labelKey: "chat",
        icon: "M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z",
        badge: "3",
      },
    ],
  },
  {
    sectionKey: "sectionContent",
    items: [
      {
        href: "/dashboard/create",
        labelKey: "createCarousel",
        icon: "M12 5v14M5 12h14",
      },
      {
        href: "/dashboard/blog-posts",
        labelKey: "blogPosts",
        icon: "M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20",
      },
      {
        href: "/dashboard/workflow",
        labelKey: "workflowBoard",
        icon: "M12 12a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z",
      },
    ],
  },
  {
    sectionKey: "sectionManagement",
    items: [
      {
        href: "/dashboard/calendar",
        labelKey: "calendar",
        icon: "M3 4h18v18H3zM16 2v4M8 2v4M3 10h18",
      },
      {
        href: "/dashboard/rubrics",
        labelKey: "rubrics",
        icon: "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M9 15l2 2 4-4",
      },
      {
        href: "/dashboard/personas",
        labelKey: "personas",
        icon: "M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2M12 7a4 4 0 1 0 0-8 4 4 0 0 0 0 8z",
      },
    ],
  },
];

function NavIcon({ path }: { path: string }) {
  return (
    <svg
      width="18"
      height="18"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      viewBox="0 0 24 24"
    >
      {path
        .split("M")
        .filter(Boolean)
        .map((seg, i) => (
          <path key={i} d={`M${seg}`} />
        ))}
    </svg>
  );
}

export default function DashboardLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const pathname = usePathname();
  const t = useTranslations("common.sidebar");

  return (
    <>
      {/* Grid Background - outside the layout container so it's not blocked by opaque backgrounds */}
      <div
        className="fixed inset-0 pointer-events-none"
        aria-hidden="true"
        style={{ perspective: "600px", overflow: "hidden", zIndex: 0 }}
      >
        <div
          className="absolute inset-[-50%] w-[200%] h-[200%]"
          style={{
            backgroundImage: `linear-gradient(rgba(0, 212, 255, 0.025) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 212, 255, 0.025) 1px, transparent 1px)`,
            backgroundSize: "60px 60px",
            transform: "rotateX(60deg)",
            animation: "grid-drift 20s linear infinite",
          }}
        />
      </div>

      {/* Scanline Overlay */}
      <div
        className="fixed inset-0 pointer-events-none"
        style={{
          zIndex: 50,
          background:
            "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0, 212, 255, 0.012) 2px, rgba(0, 212, 255, 0.012) 4px)",
        }}
      />

      <div
        className="min-h-full flex flex-col"
        style={{
          color: TEXT,
          fontFamily: "Inter, system-ui, sans-serif",
          position: "relative",
          zIndex: 1,
        }}
      >
        <div className="flex min-h-screen">
          {/* Sidebar */}
          <aside
            className="fixed top-0 left-0 h-full flex flex-col"
            style={{
              width: "240px",
              background: BG_SIDEBAR,
              borderRight: "1px solid rgba(0,212,255,0.06)",
              zIndex: 30,
            }}
          >
            <div
              style={{
                height: "56px",
                borderBottom: "1px solid rgba(0,212,255,0.06)",
                display: "flex",
                alignItems: "center",
                padding: "0 20px",
              }}
            >
              <div
                style={{
                  width: "32px",
                  height: "32px",
                  border: `2px solid ${CYAN}`,
                  borderRadius: "4px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                  fontSize: "14px",
                  fontWeight: 700,
                  color: CYAN,
                  boxShadow: `0 0 12px rgba(0,212,255,0.12), inset 0 0 12px rgba(0,212,255,0.12)`,
                }}
              >
                P
              </div>
              <div style={{ marginLeft: "12px" }}>
                <div style={{ fontSize: "16px", fontWeight: 700 }}>
                  Alter Ego
                </div>
                <div
                  style={{
                    fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                    fontSize: "9px",
                    color: TEXT_DIM,
                    letterSpacing: "0.1em",
                    textTransform: "uppercase",
                  }}
                >
                  v2.0 · Neon Shell
                </div>
              </div>
            </div>

            <nav
              style={{
                flex: 1,
                padding: "12px",
                display: "flex",
                flexDirection: "column",
                gap: "4px",
              }}
            >
              {SIDEBAR_SECTIONS.map((group) => (
                <div key={group.sectionKey}>
                  <div
                    style={{
                      fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                      fontSize: "9px",
                      textTransform: "uppercase",
                      letterSpacing: "0.15em",
                      color: TEXT_DIM,
                      padding: "12px 12px 8px",
                    }}
                  >
                    {t(group.sectionKey)}
                  </div>
                  {group.items.map((item) => {
                    const isActive = pathname === item.href;
                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "12px",
                          padding: "10px 12px",
                          borderRadius: "6px",
                          color: isActive ? CYAN : TEXT_MUTED,
                          textDecoration: "none",
                          fontSize: "13px",
                          fontWeight: isActive ? 600 : 500,
                          transition: "all 0.15s",
                          background: isActive ? CYAN_DIM : "transparent",
                        }}
                      >
                        <NavIcon path={item.icon} />
                        <span style={{ flex: 1 }}>{t(item.labelKey)}</span>
                        {item.badge && (
                          <span
                            style={{
                              fontFamily:
                                "'JetBrains Mono', ui-monospace, monospace",
                              fontSize: "10px",
                              padding: "2px 6px",
                              borderRadius: "8px",
                              background: "rgba(255,39,112,0.12)",
                              color: "#ff2770",
                              fontWeight: 700,
                            }}
                          >
                            {item.badge}
                          </span>
                        )}
                      </Link>
                    );
                  })}
                </div>
              ))}
            </nav>

            <div
              style={{
                padding: "12px",
                borderTop: "1px solid rgba(0,212,255,0.06)",
                display: "flex",
                alignItems: "center",
                gap: "10px",
              }}
            >
              <img
                src="/about-pedro.png"
                alt=""
                style={{
                  width: "28px",
                  height: "28px",
                  borderRadius: "50%",
                  border: "1px solid rgba(0,212,255,0.15)",
                  objectFit: "cover",
                }}
              />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div
                  style={{
                    fontSize: "12px",
                    fontWeight: 600,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  Pedro Marins
                </div>
                <div
                  style={{
                    fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                    fontSize: "9px",
                    color: TEXT_DIM,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  admin@alterego.app
                </div>
              </div>
              <button
                type="button"
                onClick={() => {
                  window.location.href = "/login";
                }}
                aria-label="Logout"
                title="Logout"
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: "28px",
                  height: "28px",
                  borderRadius: "6px",
                  border: "1px solid rgba(0,212,255,0.08)",
                  background: "transparent",
                  color: TEXT_MUTED,
                  cursor: "pointer",
                  fontFamily: "inherit",
                  flexShrink: 0,
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.color = CYAN;
                  e.currentTarget.style.borderColor = "rgba(0,212,255,0.25)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = TEXT_MUTED;
                  e.currentTarget.style.borderColor = "rgba(0,212,255,0.08)";
                }}
              >
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                  <polyline points="16 17 21 12 16 7" />
                  <line x1="21" y1="12" x2="9" y2="12" />
                </svg>
              </button>
            </div>
          </aside>

          {/* Main content area */}
          <div
            className="flex flex-1 flex-col min-h-screen"
            style={{ marginLeft: "240px" }}
          >
            <main
              className="flex-1"
              style={{ display: "flex", flexDirection: "column" }}
            >
              {children}
            </main>
          </div>
        </div>
      </div>
    </>
  );
}
