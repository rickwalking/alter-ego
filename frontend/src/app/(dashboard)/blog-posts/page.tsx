"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Input,
  Textarea,
  Badge,
  Alert,
  AlertDescription,
  Spinner,
} from "@/components/ui";
import { AccessibilityChecker } from "@/features/blog/components/accessibility-checker";
import { AiSuggestionPanel } from "@/features/blog/components/ai-suggestion-panel";
import { BlogPostFilters } from "@/features/blog/components/blog-post-filters";
import { ImageGenModal } from "@/features/blog/components/image-gen-modal";
import { KeyboardShortcutsHelp } from "@/features/blog/components/keyboard-shortcuts-help";
import { SeoPreview } from "@/features/blog/components/seo-preview";
import { useEditorShortcuts } from "@/features/blog/hooks/use-editor-shortcuts";
import { useBlogPosts } from "@/features/blog/hooks/use-blog-posts";
import { BlogPostEditExtras } from "@/features/workflow/components/blog-post-edit-extras";
import type { BlogPost, BlogPostCreatePayload } from "@/features/blog/types";

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-yellow-500",
  under_review: "bg-blue-500",
  approved: "bg-green-500",
  published: "bg-emerald-600",
  archived: "bg-gray-500",
};

export default function BlogPostsPage() {
  const t = useTranslations("dashboard.blogPosts");
  const {
    posts,
    loading,
    error,
    refetch,
    create,
    update,
    delete: deletePost,
    submitForReview,
    approve,
    publish,
    filters,
    setFilters,
  } = useBlogPosts();

  const [isCreating, setIsCreating] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formData, setFormData] = useState<BlogPostCreatePayload>({
    title: "",
    slug: "",
    content: {},
    excerpt: "",
    author_id: "",
  });
  const [bodyText, setBodyText] = useState("");
  const [selectedText, setSelectedText] = useState("");
  const [showImageModal, setShowImageModal] = useState(false);
  const [featuredImageUrl, setFeaturedImageUrl] = useState<string | null>(null);
  const [previousBodyText, setPreviousBodyText] = useState("");
  const [editingStatus, setEditingStatus] = useState<string>("draft");
  const [editingLockVersion, setEditingLockVersion] = useState<number>(1);
  const [showShortcuts, setShowShortcuts] = useState(false);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const filteredPosts = posts;

  const resetForm = () => {
    setFormData({ title: "", slug: "", content: {}, excerpt: "", author_id: "" });
    setBodyText("");
    setSelectedText("");
    setFeaturedImageUrl(null);
  };

  const handleCreate = async () => {
    await create(formData);
    setIsCreating(false);
    resetForm();
  };

  const handleUpdate = async (id: string) => {
    await update(id, formData, editingLockVersion);
    setEditingId(null);
    resetForm();
  };

  const startEdit = (post: BlogPost) => {
    setEditingId(post.id);
    setFormData({
      title: post.title,
      slug: post.slug,
      content: post.content,
      excerpt: post.excerpt || "",
      author_id: post.author_id || "",
      reviewer_id: post.reviewer_id || "",
      meta_title: post.meta_title || "",
      meta_description: post.meta_description || "",
    });
    const contentText =
      typeof post.content === "object" && post.content !== null && "body" in post.content
        ? String((post.content as { body?: string }).body ?? "")
        : "";
    setBodyText(contentText);
    setPreviousBodyText(contentText);
    setEditingStatus(post.status);
    setEditingLockVersion(post.lock_version ?? 1);
    setFeaturedImageUrl(post.featured_image_url ?? null);
  };

  useEditorShortcuts(
    {
      onSave: editingId ? () => void handleUpdate(editingId) : undefined,
      onSubmitReview: editingId && formData.reviewer_id
        ? () => void submitForReview(editingId, formData.reviewer_id!)
        : undefined,
      onShowHelp: () => setShowShortcuts(true),
    },
    Boolean(editingId || isCreating),
  );

  const getStatusBadge = (status: string) => (
    <div className="flex items-center gap-2">
      <div className={`w-2 h-2 rounded-full ${STATUS_COLORS[status] ?? "bg-gray-500"}`} />
      <span className="text-sm font-medium">{t(`status.${status}` as "status.draft")}</span>
    </div>
  );

  if (loading && posts.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <h1 className="text-3xl font-bold">{t("title")}</h1>
        <Button onClick={() => setIsCreating(true)} disabled={isCreating}>
          {t("createPost")}
        </Button>
      </div>

      <BlogPostFilters
        search={search}
        status={statusFilter}
        onSearchChange={(v) => {
          setSearch(v);
          setFilters({ ...filters, search: v || undefined });
        }}
        onStatusChange={(v) => {
          setStatusFilter(v);
          setFilters({ ...filters, status: v || undefined });
        }}
      />

      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {(isCreating || editingId) && (
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>{editingId ? t("editPost") : t("createNew")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 lg:grid-cols-2">
              <div className="space-y-4">
                <Field label={t("fields.title")}>
                  <Input
                    value={formData.title}
                    onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  />
                </Field>
                <Field label={t("fields.slug")}>
                  <Input
                    value={formData.slug || ""}
                    onChange={(e) => setFormData({ ...formData, slug: e.target.value })}
                  />
                </Field>
                <Field label={t("fields.excerpt")}>
                  <Textarea
                    value={formData.excerpt || ""}
                    onChange={(e) => setFormData({ ...formData, excerpt: e.target.value })}
                    rows={2}
                  />
                </Field>
                <Field label={t("fields.metaTitle")}>
                  <Input
                    value={formData.meta_title || ""}
                    onChange={(e) => setFormData({ ...formData, meta_title: e.target.value })}
                  />
                </Field>
                <Field label={t("fields.metaDescription")}>
                  <Textarea
                    value={formData.meta_description || ""}
                    onChange={(e) => setFormData({ ...formData, meta_description: e.target.value })}
                    rows={2}
                  />
                </Field>
                <Field label={t("fields.reviewerId")}>
                  <Input
                    value={formData.reviewer_id || ""}
                    onChange={(e) => setFormData({ ...formData, reviewer_id: e.target.value })}
                  />
                </Field>
                <Field label={t("fields.content")}>
                  <Textarea
                    value={bodyText}
                    onChange={(e) => {
                      setBodyText(e.target.value);
                      setFormData({ ...formData, content: { body: e.target.value } });
                    }}
                    onSelect={(e) => {
                      const target = e.target as HTMLTextAreaElement;
                      setSelectedText(target.value.substring(target.selectionStart, target.selectionEnd));
                    }}
                    rows={8}
                  />
                </Field>
              </div>
              <div className="space-y-4">
                <SeoPreview
                  postId={editingId}
                  title={formData.title}
                  slug={formData.slug || ""}
                  metaTitle={formData.meta_title ?? undefined}
                  metaDescription={formData.meta_description ?? undefined}
                  excerpt={formData.excerpt ?? undefined}
                  featuredImageUrl={featuredImageUrl}
                />
                <AccessibilityChecker postId={editingId} />
              </div>
            </div>
            {editingId && (
              <>
                <AiSuggestionPanel
                  postId={editingId}
                  selectedText={selectedText || bodyText}
                  onApplySuggestion={(text) => {
                    setBodyText(text);
                    setFormData({ ...formData, content: { body: text } });
                  }}
                />
                <Button type="button" variant="outline" onClick={() => setShowImageModal(true)}>
                  {t("actions.generateImage")}
                </Button>
                {featuredImageUrl && (
                  <img src={featuredImageUrl} alt="Featured" className="h-12 w-12 rounded object-cover" />
                )}
                <ImageGenModal
                  postId={editingId}
                  open={showImageModal}
                  onClose={() => setShowImageModal(false)}
                  onImageGenerated={setFeaturedImageUrl}
                />
                <BlogPostEditExtras
                  postId={editingId}
                  title={formData.title}
                  status={editingStatus}
                  bodyText={bodyText}
                  previousBodyText={previousBodyText}
                  onScheduled={() => void refetch()}
                />
              </>
            )}
            <div className="flex gap-2">
              <Button onClick={() => (editingId ? void handleUpdate(editingId) : void handleCreate())}>
                {editingId ? t("actions.update") : t("actions.create")}
              </Button>
              <Button variant="outline" onClick={() => { setIsCreating(false); setEditingId(null); resetForm(); }}>
                {t("actions.cancel")}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <KeyboardShortcutsHelp open={showShortcuts} onClose={() => setShowShortcuts(false)} />

      <div className="grid gap-4">
        {filteredPosts.length === 0 ? (
          <Card>
            <CardContent className="py-8 text-center text-muted-foreground">
              {search || statusFilter ? t("noResults") : t("empty")}
            </CardContent>
          </Card>
        ) : (
          filteredPosts.map((post) => (
            <Card key={post.id}>
              <CardHeader className="pb-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <CardTitle className="text-xl">{post.title}</CardTitle>
                    {getStatusBadge(post.status)}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {post.status === "draft" && post.reviewer_id && (
                      <Button size="sm" onClick={() => void submitForReview(post.id, post.reviewer_id!)}>
                        {t("actions.submitReview")}
                      </Button>
                    )}
                    {post.status === "under_review" && (
                      <Button size="sm" variant="outline" onClick={() => void approve(post.id)}>
                        {t("actions.approve")}
                      </Button>
                    )}
                    {post.status === "approved" && (
                      <Button size="sm" onClick={() => void publish(post.id)}>
                        {t("actions.publish")}
                      </Button>
                    )}
                    <Button variant="outline" size="sm" onClick={() => startEdit(post)}>
                      {t("actions.edit")}
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => {
                        if (window.confirm(t("confirmDelete"))) void deletePost(post.id);
                      }}
                    >
                      {t("actions.delete")}
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {post.excerpt && <p className="text-sm text-muted-foreground mb-4">{post.excerpt}</p>}
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="text-sm font-medium mb-2 block">{label}</label>
      {children}
    </div>
  );
}
