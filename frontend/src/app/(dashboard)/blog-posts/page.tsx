"use client";

import { useState } from "react";
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
import { useBlogPosts } from "@/features/blog/hooks/use-blog-posts";
import type { BlogPost, BlogPostCreatePayload } from "@/features/blog/types";

const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  draft: { label: "Draft", color: "bg-yellow-500" },
  under_review: { label: "Under Review", color: "bg-blue-500" },
  approved: { label: "Approved", color: "bg-green-500" },
  published: { label: "Published", color: "bg-emerald-600" },
  archived: { label: "Archived", color: "bg-gray-500" },
};

export default function BlogPostsPage() {
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

  const handleCreate = async () => {
    try {
      await create(formData);
      setIsCreating(false);
      resetForm();
    } catch (err) {
      console.error("Failed to create blog post:", err);
    }
  };

  const handleUpdate = async (id: string) => {
    try {
      await update(id, formData);
      setEditingId(null);
      resetForm();
    } catch (err) {
      console.error("Failed to update blog post:", err);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm("Are you sure you want to delete this blog post?")) return;
    try {
      await deletePost(id);
    } catch (err) {
      console.error("Failed to delete blog post:", err);
    }
  };

  const resetForm = () => {
    setFormData({
      title: "",
      slug: "",
      content: {},
      excerpt: "",
      author_id: "",
    });
  };

  const startEdit = (post: BlogPost) => {
    setEditingId(post.id);
    setFormData({
      title: post.title,
      slug: post.slug,
      content: post.content,
      excerpt: post.excerpt || "",
      author_id: post.author_id || "",
    });
  };

  const handleSubmitForReview = async (id: string) => {
    try {
      await submitForReview(id);
    } catch (err) {
      console.error("Failed to submit for review:", err);
    }
  };

  const handleApprove = async (id: string) => {
    try {
      await approve(id, "current-user");
    } catch (err) {
      console.error("Failed to approve:", err);
    }
  };

  const handlePublish = async (id: string) => {
    try {
      await publish(id);
    } catch (err) {
      console.error("Failed to publish:", err);
    }
  };

  const getStatusBadge = (status: string) => {
    const config = STATUS_CONFIG[status] || { label: status, color: "bg-gray-500" };
    return (
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${config.color}`} />
        <span className="text-sm font-medium">{config.label}</span>
      </div>
    );
  };

  const getWorkflowActions = (post: BlogPost) => {
    const actions = [];

    if (post.status === "draft") {
      actions.push(
        <Button key="review" size="sm" onClick={() => handleSubmitForReview(post.id)}>
          Submit for Review
        </Button>
      );
    }

    if (post.status === "under_review") {
      actions.push(
        <Button key="approve" size="sm" variant="outline" onClick={() => handleApprove(post.id)}>
          Approve
        </Button>
      );
    }

    if (post.status === "approved") {
      actions.push(
        <Button key="publish" size="sm" onClick={() => handlePublish(post.id)}>
          Publish
        </Button>
      );
    }

    return actions;
  };

  if (loading && posts.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 px-4">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold">Blog Posts</h1>
        <Button onClick={() => setIsCreating(true)} disabled={isCreating}>
          Create Post
        </Button>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {(isCreating || editingId) && (
        <Card className="mb-8">
          <CardHeader>
            <CardTitle>{editingId ? "Edit Blog Post" : "Create New Blog Post"}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium mb-2 block">Title</label>
              <Input
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                placeholder="Enter post title..."
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Slug</label>
              <Input
                value={formData.slug || ""}
                onChange={(e) => setFormData({ ...formData, slug: e.target.value })}
                placeholder="url-friendly-slug"
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Excerpt</label>
              <Textarea
                value={formData.excerpt || ""}
                onChange={(e) => setFormData({ ...formData, excerpt: e.target.value })}
                placeholder="Brief summary of the post..."
                rows={3}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">Author ID</label>
              <Input
                value={formData.author_id || ""}
                onChange={(e) => setFormData({ ...formData, author_id: e.target.value })}
                placeholder="author-identifier"
              />
            </div>
            <div className="flex gap-2">
              <Button
                onClick={() => {
                  if (editingId) {
                    handleUpdate(editingId);
                  } else {
                    handleCreate();
                  }
                }}
              >
                {editingId ? "Update" : "Create"}
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setIsCreating(false);
                  setEditingId(null);
                  resetForm();
                }}
              >
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4">
        {posts.length === 0 ? (
          <Card>
            <CardContent className="py-8 text-center text-muted-foreground">
              No blog posts yet. Create your first post to get started.
            </CardContent>
          </Card>
        ) : (
          posts.map((post) => (
            <Card key={post.id}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <CardTitle className="text-xl">{post.title}</CardTitle>
                    {getStatusBadge(post.status)}
                  </div>
                  <div className="flex gap-2">
                    {getWorkflowActions(post)}
                    <Button variant="outline" size="sm" onClick={() => startEdit(post)}>
                      Edit
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => handleDelete(post.id)}
                    >
                      Delete
                    </Button>
                  </div>
                </div>
                <div className="flex items-center gap-4 text-sm text-muted-foreground mt-2">
                  <span>Slug: {post.slug}</span>
                  {post.author_id && <span>Author: {post.author_id}</span>}
                  {post.published_at && (
                    <span>Published: {new Date(post.published_at).toLocaleDateString()}</span>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                {post.excerpt && (
                  <p className="text-sm text-muted-foreground mb-4">{post.excerpt}</p>
                )}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <span className="text-muted-foreground">Views:</span> {post.view_count}
                  </div>
                  <div>
                    <span className="text-muted-foreground">Likes:</span> {post.like_count}
                  </div>
                  <div>
                    <span className="text-muted-foreground">Comments:</span> {post.comment_count}
                  </div>
                  <div>
                    <span className="text-muted-foreground">Shares:</span> {post.share_count}
                  </div>
                </div>
                {post.keywords.length > 0 && (
                  <div className="mt-4 flex flex-wrap gap-2">
                    {post.keywords.map((keyword) => (
                      <Badge key={keyword} variant="secondary">
                        {keyword}
                      </Badge>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
