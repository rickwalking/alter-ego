/**
 * Section editor prop types (AE-0424; colocated per AE-0144).
 */

import type {
  BlogDocument,
  BlogImage,
  BlogSection,
} from "@/schemas/blog-document";
import type { BlogDocumentIssue } from "../../editor-content";
import type { BlogEditorError, SlotStatus } from "../../hooks/types";
import type {
  BlogContentLanguage,
  BlogImageSlotRef,
} from "../../lib/editor-document";
import type { BlogVoicePersona } from "../../types";

export interface ImageSlotProps {
  /** DOM id prefix (unique per slot). */
  slotId: string;
  label: string;
  image: BlogImage | null;
  status: SlotStatus;
  readOnly: boolean;
  /** Alt shown when the image is generated (defaults server-side too). */
  issue: BlogDocumentIssue | null;
  onGenerate: (prompt: string | null) => void;
  onChange: (image: BlogImage | null) => void;
}

export interface ImageTextsProps {
  slotId: string;
  image: BlogImage;
  readOnly: boolean;
  issue: BlogDocumentIssue | null;
  onChange: (image: BlogImage | null) => void;
}

export interface SectionCardProps {
  section: BlogSection;
  index: number;
  count: number;
  language: BlogContentLanguage;
  readOnly: boolean;
  issue: BlogDocumentIssue | null;
  imageStatus: SlotStatus;
  rewriteStatus: SlotStatus;
  onChange: (
    patch: Partial<Pick<BlogSection, "heading" | "body_md" | "image">>,
  ) => void;
  onMove: (delta: number) => void;
  onDelete: () => void;
  onGenerateImage: (prompt: string | null) => void;
  onRewrite: () => void;
  onSelectText: (text: string) => void;
}

export interface LanguageTabsProps {
  language: BlogContentLanguage;
  hasEnglish: boolean;
  translationStatus: SlotStatus;
  onChange: (language: BlogContentLanguage) => void;
  onGenerateTranslation: () => void;
}

export interface VoiceScoreProps {
  quality: unknown;
  personas: BlogVoicePersona[];
  personaId: string | null;
  onPersonaChange: (personaId: string | null) => void;
}

export interface MigrationBannerProps {
  detail: string | null;
}

export interface ReviewBarProps {
  status: string;
  scheduledPublishAt: string | null;
  /** Pending edits or a running action disable the workflow controls. */
  disabled: boolean;
  /** The failed review/publish action, shown in the bar (AE-0438, F-11). */
  error: BlogEditorError | null;
  onSubmitReview: (reviewerId: string | null) => void;
  onApprove: () => void;
  onReject: (reason: string) => void;
  onPublish: () => void;
  onPublishNow: () => void;
  onUnpublish: () => void;
  onSchedule: (scheduledAtIso: string) => void;
  onCancelSchedule: () => void;
}

export interface ScheduleControlProps {
  scheduledPublishAt: string | null;
  disabled: boolean;
  onSchedule: (scheduledAtIso: string) => void;
  onCancelSchedule: () => void;
}

/** A text selection inside one section's body (for the AI panel). */
export interface SectionSelection {
  sectionId: string;
  text: string;
}

export interface BlogSectionEditorProps {
  document: BlogDocument;
  language: BlogContentLanguage;
  validation: Record<string, BlogDocumentIssue>;
  statusOf: (key: string) => SlotStatus;
  onLanguageChange: (language: BlogContentLanguage) => void;
  onDocumentChange: (edit: (document: BlogDocument) => BlogDocument) => void;
  onGenerateImage: (slot: BlogImageSlotRef, prompt: string | null) => void;
  onRewrite: (sectionId: string) => void;
  onGenerateTranslation: () => void;
  onSelectText: (selection: SectionSelection) => void;
}
