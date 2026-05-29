import {
  NEON_AMBER,
  NEON_CYAN,
  NEON_MAGENTA,
  NEON_RED,
  NEON_TEAL,
} from "@/constants/neon";

export const PERSONA_COLORS = {
  cyan: NEON_CYAN,
  magenta: NEON_MAGENTA,
  teal: NEON_TEAL,
  amber: NEON_AMBER,
  red: NEON_RED,
} as const;

export type PersonaAccent = keyof typeof PERSONA_COLORS;

export interface PersonaData {
  initials: string;
  name: string;
  title: string;
  traits: string[];
  description: string;
  carousels: number;
  score: string;
  status: "active" | "inactive";
  accent: PersonaAccent;
}

export const PERSONAS: PersonaData[] = [
  {
    initials: "TS",
    name: "Tech Specialist",
    title: "Deep technical, data-driven voice",
    traits: ["Precise", "Data-heavy", "Technical", "Concise"],
    description:
      "Speaks to engineers with assumed knowledge. Uses correct terminology, cites benchmarks, avoids fluff. Ideal for deep-dive carousels and technical analysis.",
    carousels: 12,
    score: "94%",
    status: "active",
    accent: "cyan",
  },
  {
    initials: "EL",
    name: "Engineering Leader",
    title: "Strategic, big-picture voice",
    traits: ["Strategic", "High-level", "Opinionated", "Confident"],
    description:
      "Tailored for engineering managers and team leads. Focuses on tradeoffs, team impact, and architectural decisions with authority.",
    carousels: 8,
    score: "91%",
    status: "active",
    accent: "magenta",
  },
  {
    initials: "PM",
    name: "Product Manager",
    title: "Value-focused, business-aware",
    traits: ["Pragmatic", "Business-aware", "Clear", "Concise"],
    description:
      "Bridges technical depth with business value. Highlights ROI, timelines, and competitive positioning for decision-makers.",
    carousels: 5,
    score: "87%",
    status: "active",
    accent: "amber",
  },
  {
    initials: "SA",
    name: "Security Analyst",
    title: "Cautious, precise, risk-aware",
    traits: ["Risk-aware", "Methodical", "Cautious", "Detailed"],
    description:
      "Authoritative voice for security content. Emphasizes threat modeling, mitigation strategies, and compliance considerations.",
    carousels: 6,
    score: "89%",
    status: "inactive",
    accent: "teal",
  },
];

export function dimPersonaColor(hex: string): string {
  return `${hex}1F`;
}
