import {
  NEON_AMBER,
  NEON_AMBER_DIM,
  NEON_CYAN,
  NEON_CYAN_DIM,
  NEON_GREEN,
  NEON_MAGENTA,
  NEON_MAGENTA_DIM,
  NEON_PURPLE,
  NEON_RED,
  NEON_TEAL,
  NEON_TEAL_DIM,
} from "@/constants/neon";

export const WORKFLOW_CYAN = NEON_CYAN;
export const WORKFLOW_MAGENTA = NEON_MAGENTA;
export const WORKFLOW_TEAL = NEON_TEAL;
export const WORKFLOW_AMBER = NEON_AMBER;
export const WORKFLOW_PURPLE = NEON_PURPLE;
export const WORKFLOW_GREEN = NEON_GREEN;

export type ApprovalStatus = "pending" | "approved" | "rejected" | "awaiting_human";

export const APPROVAL_STYLES: Record<ApprovalStatus, { bg: string; color: string }> = {
  pending: { bg: NEON_AMBER_DIM, color: NEON_AMBER },
  approved: { bg: "rgba(34,197,94,0.12)", color: NEON_GREEN },
  rejected: { bg: "rgba(239,68,68,0.12)", color: NEON_RED },
  awaiting_human: { bg: NEON_CYAN_DIM, color: NEON_CYAN },
};

export interface WorkflowCardData {
  title: string;
  description: string;
  phase: string;
  assignee: string;
  assigneeBg: string;
  assigneeColor: string;
  approvalStatus: ApprovalStatus;
}

export interface WorkflowColumnData {
  id: string;
  label: string;
  color: string;
  cards: WorkflowCardData[];
}

export const WORKFLOW_COLUMNS: WorkflowColumnData[] = [
  { id: "brief", label: "Brief", color: "#a0a0a0", cards: [] },
  {
    id: "research",
    label: "Research",
    color: WORKFLOW_CYAN,
    cards: [
      {
        title: "DeepSeek V4 Analysis",
        description:
          "Research open-source LLM benchmarks, architecture innovations, and pricing strategy from Twitter, GitHub, and tech blogs.",
        phase: "research",
        assignee: "PM",
        assigneeBg: NEON_CYAN_DIM,
        assigneeColor: WORKFLOW_CYAN,
        approvalStatus: "awaiting_human",
      },
    ],
  },
  { id: "outline", label: "Outline", color: WORKFLOW_TEAL, cards: [] },
  {
    id: "content",
    label: "Content",
    color: WORKFLOW_GREEN,
    cards: [
      {
        title: "SpaceX Starship Update",
        description:
          "Slide content for SpaceX carousel. 5/5 slides completed. Persona score: 78%",
        phase: "content",
        assignee: "AL",
        assigneeBg: "rgba(34,197,94,0.12)",
        assigneeColor: WORKFLOW_GREEN,
        approvalStatus: "approved",
      },
      {
        title: "AI Safety Regulations",
        description:
          "Drafting regulatory landscape carousel. 3/5 slides in progress.",
        phase: "content",
        assignee: "JD",
        assigneeBg: NEON_TEAL_DIM,
        assigneeColor: WORKFLOW_TEAL,
        approvalStatus: "pending",
      },
    ],
  },
  {
    id: "design",
    label: "Design",
    color: WORKFLOW_MAGENTA,
    cards: [
      {
        title: "Cybersecurity Trends",
        description:
          "Design tokens generated. Color theme: cyberpunk. Design tokens and layout approved.",
        phase: "design",
        assignee: "SK",
        assigneeBg: NEON_MAGENTA_DIM,
        assigneeColor: WORKFLOW_MAGENTA,
        approvalStatus: "awaiting_human",
      },
    ],
  },
  { id: "images", label: "Images", color: WORKFLOW_AMBER, cards: [] },
  {
    id: "final_review",
    label: "Final Review",
    color: WORKFLOW_PURPLE,
    cards: [
      {
        title: "Kubernetes Security Guide",
        description:
          "All phases complete. Ready for final approval. Persona score: 82%",
        phase: "final_review",
        assignee: "PM",
        assigneeBg: "rgba(168,85,247,0.12)",
        assigneeColor: WORKFLOW_PURPLE,
        approvalStatus: "awaiting_human",
      },
    ],
  },
];
