/**
 * Custom hook for managing blog posts
 */

import { useState, useEffect } from 'react';
import type { BlogPost, BlogPostCreatePayload, BlogPostUpdatePayload } from '../types';

const API_BASE = '/api';

export function useBlogPosts() {
  const [posts, setPosts] = useState<BlogPost[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPosts = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/blog-posts`);
      if (!response.ok) {
        throw new Error('Failed to fetch blog posts');
      }
      const data = await response.json();
      setPosts(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const createPost = async (data: BlogPostCreatePayload) => {
    try {
      const response = await fetch(`${API_BASE}/blog-posts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!response.ok) {
        throw new Error('Failed to create blog post');
      }
      const post = await response.json();
      setPosts(prev => [post, ...prev]);
      return post;
    } catch (err) {
      throw err;
    }
  };

  const updatePost = async (id: string, data: BlogPostUpdatePayload) => {
    try {
      const response = await fetch(`${API_BASE}/blog-posts/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!response.ok) {
        throw new Error('Failed to update blog post');
      }
      const post = await response.json();
      setPosts(prev => prev.map(p => p.id === id ? post : p));
      return post;
    } catch (err) {
      throw err;
    }
  };

  const deletePost = async (id: string) => {
    try {
      const response = await fetch(`${API_BASE}/blog-posts/${id}`, {
        method: 'DELETE',
      });
      if (!response.ok) {
        throw new Error('Failed to delete blog post');
      }
      setPosts(prev => prev.filter(p => p.id !== id));
      return true;
    } catch (err) {
      throw err;
    }
  };

  const submitForReview = async (id: string) => {
    try {
      const response = await fetch(`${API_BASE}/blog-posts/${id}/submit-review`, {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error('Failed to submit for review');
      }
      await fetchPosts();
      return true;
    } catch (err) {
      throw err;
    }
  };

  const approvePost = async (id: string, reviewerId: string) => {
    try {
      const response = await fetch(`${API_BASE}/blog-posts/${id}/approve?reviewer_id=${reviewerId}`, {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error('Failed to approve blog post');
      }
      await fetchPosts();
      return true;
    } catch (err) {
      throw err;
    }
  };

  const publishPost = async (id: string) => {
    try {
      const response = await fetch(`${API_BASE}/blog-posts/${id}/publish`, {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error('Failed to publish blog post');
      }
      await fetchPosts();
      return true;
    } catch (err) {
      throw err;
    }
  };

  useEffect(() => {
    fetchPosts();
  }, []);

  return {
    posts,
    loading,
    error,
    refetch: fetchPosts,
    create: createPost,
    update: updatePost,
    delete: deletePost,
    submitForReview,
    approve: approvePost,
    publish: publishPost,
  };
}
