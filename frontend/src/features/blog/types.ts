/**
 * Blog Post Types
 */

export interface BlogPost {
  id: string;
  project_id?: string | null;
  title: string;
  slug: string;
  status: string;
  content: Record<string, unknown>;
  excerpt?: string | null;
  featured_image_url?: string | null;
  author_id?: string | null;
  reviewer_id?: string | null;
  editor_comments: string[];
  version_history: string[];
  sources: string[];
  citations: Record<string, unknown>[];
  ai_suggestions: Record<string, unknown>[];
  ai_generation_metadata: Record<string, unknown>;
  meta_title?: string | null;
  meta_description?: string | null;
  keywords: string[];
  canonical_url?: string | null;
  view_count: number;
  like_count: number;
  comment_count: number;
  share_count: number;
  created_at: string;
  updated_at: string;
  submitted_for_review_at?: string | null;
  approved_at?: string | null;
  published_at?: string | null;
  scheduled_publish_at?: string | null;
  lock_version: number;
}

export interface BlogPostCreatePayload {
  title: string;
  slug?: string | null;
  content?: Record<string, unknown>;
  excerpt?: string | null;
  featured_image_url?: string | null;
  meta_title?: string | null;
  meta_description?: string | null;
  keywords?: string[];
  author_id?: string | null;
  reviewer_id?: string | null;
  sources?: string[];
  citations?: Record<string, unknown>[];
}

export interface BlogPostUpdatePayload {
  title?: string | null;
  slug?: string | null;
  content?: Record<string, unknown> | null;
  excerpt?: string | null;
  featured_image_url?: string | null;
  meta_title?: string | null;
  meta_description?: string | null;
  keywords?: string[] | null;
  author_id?: string | null;
  reviewer_id?: string | null;
  status?: string | null;
  sources?: string[] | null;
  citations?: Record<string, unknown>[] | null;
}
