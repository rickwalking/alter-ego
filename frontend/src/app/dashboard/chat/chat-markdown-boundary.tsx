"use client";

import { Component } from "react";

interface ChatMarkdownBoundaryProps {
  /** Shown instead when rendering the children throws. */
  fallback: React.ReactNode;
  children: React.ReactNode;
}

interface ChatMarkdownBoundaryState {
  failed: boolean;
}

/**
 * Keeps one reply's rendering failure inside its bubble: the plain text is
 * shown instead of the markdown, and the rest of the chat keeps working.
 */
export class ChatMarkdownBoundary extends Component<
  ChatMarkdownBoundaryProps,
  ChatMarkdownBoundaryState
> {
  override state: ChatMarkdownBoundaryState = { failed: false };

  static getDerivedStateFromError(): ChatMarkdownBoundaryState {
    return { failed: true };
  }

  override render(): React.ReactNode {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}
