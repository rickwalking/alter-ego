"use client";

import type { ReactNode } from "react";

/* ── Types ── */
type CT = "carousel" | "blog" | "meeting" | "management";
type ST = "published" | "approved" | "in_progress" | "awaiting_human";
interface Evt { title: string; contentType: CT; status?: ST }
interface Day { day: number; cur: boolean; today: boolean; events: Evt[] }

/* ── Color Tokens ── */
const C = {
  cyan: "#00d4ff", cD: "rgba(0,212,255,0.12)", cG: "rgba(0,212,255,0.08)",
  magenta: "#ff2770", teal: "#0ac5a8", amber: "#f59e0b", purple: "#a855f7", green: "#22c55e",
  aD: "rgba(245,158,11,0.12)", pD: "rgba(168,85,247,0.12)",
  bg: "#060a12", card: "#0d1324",
  txt: "rgba(255,255,255,0.88)", tM: "rgba(255,255,255,0.55)", tD: "rgba(255,255,255,0.3)",
  bdr: "rgba(0,212,255,0.06)",
} as const;

const CT_META: Record<CT, { c: string; d: string; l: string }> = {
  carousel: { c: C.cyan, d: C.cD, l: "carousel" },
  blog: { c: C.teal, d: "rgba(10,197,168,0.12)", l: "blog" },
  meeting: { c: C.amber, d: C.aD, l: "meeting" },
  management: { c: C.purple, d: C.pD, l: "management" },
};

const ST_META: Record<ST, { c: string; b: string; l: string }> = {
  published: { c: "#27ae60", b: "rgba(46,204,113,0.15)", l: "published" },
  approved: { c: C.cyan, b: "rgba(0,212,255,0.15)", l: "approved" },
  in_progress: { c: C.cyan, b: "rgba(0,212,255,0.15)", l: "in_progress" },
  awaiting_human: { c: "#ec3768", b: "rgba(236,56,153,0.15)", l: "awaiting_human" },
};

const HDRS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

const LEGEND = [
  { l: "Carousel", c: C.cyan }, { l: "Blog Post", c: C.teal }, { l: "Draft", c: C.magenta },
  { l: "Meeting", c: C.amber }, { l: "Review", c: C.purple }, { l: "Published", c: C.green },
];

/* ── Calendar Grid ── */
const TODAY = 28;
const EVT: Record<number, Evt[]> = {
  22: [{ title: "RAG Pipeline", contentType: "blog", status: "published" }],
  24: [{ title: "Sonnet 4 vs GPT-5", contentType: "carousel", status: "approved" }],
  26: [
    { title: "GitHub Leak Post", contentType: "blog", status: "awaiting_human" },
    { title: "K8s Review", contentType: "carousel", status: "in_progress" },
  ],
  27: [{ title: "Security Sync", contentType: "meeting" }],
  28: [{ title: "Persona Review", contentType: "management" }],
  29: [{ title: "K8s Guide Pub.", contentType: "carousel", status: "published" }],
  30: [{ title: "AI Safety Research", contentType: "blog", status: "published" }],
};

function buildDays(): Day[] {
  const d: Day[] = [];
  for (const day of [27, 28, 29, 30]) d.push({ day, cur: false, today: false, events: [] });
  for (let i = 1; i <= 31; i++) d.push({ day: i, cur: true, today: i === TODAY, events: EVT[i] ?? [] });
  return d;
}

/* ── SVG Icons (compact) ── */
function SvgIcon({ name, size = 16 }: { name: string; size?: number }): ReactNode {
  const s = <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />;
  const ch: Record<string, ReactNode> = {
    left: <polyline points="15 18 9 12 15 6" />,
    right: <polyline points="9 18 15 12 9 6" />,
    plus: <><path d="M12 5v14" /><path d="M5 12h14" /></>,
    sync: <><polyline points="23 4 23 10 17 10" /><polyline points="1 20 1 14 7 14" /><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" /></>,
    grid: <><rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" /><rect x="3" y="14" width="7" height="7" /><rect x="14" y="14" width="7" height="7" /></>,
    file: <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20" />,
    cal: <><rect x="3" y="4" width="18" height="18" rx="2" /><path d="M16 2v4" /><path d="M8 2v4" /><path d="M3 10h18" /></>,
    user: <><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={name === "plus" ? 2.5 : 2} strokeLinecap="round" strokeLinejoin="round">{ch[name]}</svg>;
}

/* ── Style helpers ── */
const btnGhost: React.CSSProperties = {
  display: "inline-flex", alignItems: "center", gap: 8, padding: "6px 12px",
  borderRadius: 6, fontSize: 12, fontWeight: 600, lineHeight: 1, cursor: "pointer",
  border: "1px solid rgba(0,212,255,0.25)", background: "transparent", color: C.cyan, fontFamily: "inherit",
};

const fCenter: React.CSSProperties = { display: "flex", alignItems: "center" };
const mono = "'JetBrains Mono', ui-monospace, monospace";

/* ═══════════════════════════════════════════
   Page Component
   ═══════════════════════════════════════════ */

export default function CalendarPage() {
  const days = buildDays();

  return (
    <div style={{ fontFamily: "'Inter', system-ui, -apple-system, sans-serif", color: C.txt, background: C.bg, minHeight: "100vh" }}>
      {/* ── Top Bar ── */}
      <div style={{ height: 56, ...fCenter, justifyContent: "space-between", padding: "0 32px", borderBottom: `1px solid ${C.bdr}`, background: "rgba(6,10,18,0.6)", backdropFilter: "blur(12px)", position: "sticky", top: 0, zIndex: 50 }}>
        <div style={{ ...fCenter, gap: 12 }}>
          <span style={{ fontSize: 16, fontWeight: 700, color: C.txt, letterSpacing: "-0.02em" }}>Calendar</span>
          <span style={{ fontFamily: mono, fontSize: 11, color: C.tD }}>/ <span style={{ color: C.tM }}>content calendar</span></span>
        </div>
        <div style={{ ...fCenter, gap: 16 }}>
          <button type="button" style={btnGhost}><SvgIcon name="sync" size={14} /> Sync</button>
          <button type="button" style={{ ...btnGhost, border: "none", background: `linear-gradient(135deg,${C.cyan} 0%,#0090b0 100%)`, color: C.bg, boxShadow: `0 0 16px ${C.cD}` }}><SvgIcon name="plus" size={14} /> Schedule Post</button>
        </div>
      </div>

      {/* ── Page Content ── */}
      <div style={{ padding: "28px 32px" }}>
        {/* Calendar Header */}
        <div style={{ ...fCenter, justifyContent: "space-between", marginBottom: 20 }}>
          <div style={{ ...fCenter, gap: 12 }}>
            <button type="button" aria-label="Previous month" style={{ ...btnGhost, padding: 8, lineHeight: 0, justifyContent: "center" }}><SvgIcon name="left" /></button>
            <h2 style={{ fontSize: 20, fontWeight: 800, color: C.txt, letterSpacing: "-0.02em", margin: 0 }}>May 2026</h2>
            <button type="button" aria-label="Next month" style={{ ...btnGhost, padding: 8, lineHeight: 0, justifyContent: "center" }}><SvgIcon name="right" /></button>
            <button type="button" style={{ ...btnGhost, marginLeft: 8 }}>Today</button>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            {["Month", "Week", "Day"].map((v) => (
              <button key={v} type="button" style={{ ...btnGhost, background: v === "Month" ? C.cD : "transparent" }}>{v}</button>
            ))}
          </div>
        </div>

        {/* ── Calendar Grid ── */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(7,1fr)", gap: 1, background: C.cG, borderRadius: 8, overflow: "hidden", border: `1px solid rgba(0,212,255,0.06)` }}>
          {HDRS.map((h) => (
            <div key={h} style={{ padding: 10, textAlign: "center", fontFamily: mono, fontSize: 10, textTransform: "uppercase", letterSpacing: 2, color: C.tD, background: "rgba(6,10,18,0.5)", fontWeight: 700 }}>{h}</div>
          ))}
          {days.filter((d) => d.cur).length === 0 ? (
            <div style={{ gridColumn: "1 / -1", padding: "60px 20px", textAlign: "center", color: C.tD }}>
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ margin: "0 auto 16px", display: "block", opacity: 0.3 }}>
                <rect x="3" y="4" width="18" height="18" rx="2" /><path d="M16 2v4" /><path d="M8 2v4" /><path d="M3 10h18" />
              </svg>
              <p style={{ fontSize: 15, color: C.tM, margin: 0 }}>No scheduled content this month</p>
              <p style={{ fontSize: 12, marginTop: 8, color: C.tD }}>Schedule a post or carousel to see it on the calendar.</p>
            </div>
          ) : (
            days.map((cell, i) => (
              <div key={`${cell.day}-${i}`} tabIndex={0} role="gridcell" style={{ minHeight: 100, padding: 8, background: cell.today ? C.cD : C.card, border: cell.today ? "1px solid rgba(0,212,255,0.2)" : "none", cursor: "pointer", opacity: cell.cur ? 1 : 0.3 }}>
                <div style={{ fontFamily: mono, fontSize: 13, color: cell.today ? C.cyan : C.tM, fontWeight: 600, marginBottom: 6 }}>{cell.day}</div>
                {cell.events.map((e, ei) => {
                  const ct = CT_META[e.contentType];
                  return (
                    <div key={`${e.title}-${ei}`}>
                      <div tabIndex={0} role="button" style={{ padding: "2px 6px", borderRadius: 3, fontSize: 10, marginBottom: 2, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", cursor: "pointer", background: e.contentType === "meeting" ? C.aD : ct.d, color: e.contentType === "meeting" ? C.amber : ct.c }}>{e.title}</div>
                      <div style={{ ...fCenter, gap: 4, marginBottom: 4, fontSize: 9, fontFamily: mono, color: C.tD }}><SvgIcon name={{ carousel: "grid", blog: "file", meeting: "cal", management: "user" }[e.contentType]} size={9} /> {ct.l}</div>
                      {e.status && <div style={{ fontSize: 9, padding: "1px 6px", borderRadius: 3, fontFamily: mono, background: ST_META[e.status].b, color: ST_META[e.status].c, display: "inline-block" }}>{ST_META[e.status].l}</div>}
                      <div style={{ fontSize: 8, color: C.tM, marginTop: 2 }}>May {cell.day}</div>
                    </div>
                  );
                })}
              </div>
            ))
          )}
        </div>

        {/* ── Legend ── */}
        <div style={{ display: "flex", gap: 16, marginTop: 16, flexWrap: "wrap" }}>
          {LEGEND.map((item) => (
            <div key={item.l} style={{ ...fCenter, gap: 6, fontSize: 11, color: C.tD, cursor: "pointer" }}>
              <span style={{ width: 8, height: 8, borderRadius: "50%", background: item.c, flexShrink: 0 }} />{item.l}
            </div>
          ))}
        </div>
      </div>

      {/* ── Responsive ── */}
      <style>{`@media(max-width:768px){div[role="gridcell"]{min-height:60px!important;padding:4px!important}div[role="gridcell"]>div:first-child{font-size:11px!important}}`}</style>
    </div>
  );
}
