"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useDeleteCarousel } from "@/modules/editorial";
import { useAuth } from "@/hooks/use-auth";
import { ROUTE_PATHS } from "@/constants/api";
import type { CarouselDesignResponse } from "@/schemas/carousel";

interface BlogPostAdminPanelProps {
  projectId: string;
  design: CarouselDesignResponse;
}

export function BlogPostAdminPanel({
  projectId,
  design,
}: BlogPostAdminPanelProps) {
  const t = useTranslations("blog.admin");
  const router = useRouter();
  const deleteMutation = useDeleteCarousel();
  const [showConfirm, setShowConfirm] = useState(false);
  const { user, isAdmin } = useAuth();

  if (!user || !isAdmin) {
    return null;
  }

  const handleDelete = async () => {
    try {
      await deleteMutation.mutateAsync(projectId);
      setShowConfirm(false);
      router.push(ROUTE_PATHS.HOME);
      router.refresh();
    } catch {
      // Mutation error is surfaced by the hook; just close the dialog
      // so the user can see the page behind (or retry).
      setShowConfirm(false);
    }
  };

  return (
    <>
      <div
        className="mb-6 flex flex-wrap items-center gap-2 rounded-lg border px-4 py-3"
        style={{
          borderColor: `${design.colors.primary}33`,
          background: `${design.colors.primary}0D`,
        }}
      >
        <span
          className="mr-2 text-xs font-bold uppercase tracking-widest"
          style={{ color: design.colors.primary }}
        >
          {t("title")}
        </span>
        <Link
          href={ROUTE_PATHS.CREATE_PUBLISH(projectId)}
          className="inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-opacity hover:opacity-80"
          style={{
            background: design.colors.primary,
            color: design.colors.bg,
          }}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8" />
            <polyline points="16 6 12 2 8 6" />
            <line x1="12" y1="2" x2="12" y2="15" />
          </svg>
          {t("publish")}
        </Link>
        <button
          type="button"
          onClick={() => setShowConfirm(true)}
          disabled={deleteMutation.isPending}
          className="inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-opacity hover:opacity-80 disabled:opacity-50"
          style={{
            background: `${design.colors.accent}20`,
            color: design.colors.accent,
            border: `1px solid ${design.colors.accent}40`,
          }}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <polyline points="3 6 5 6 21 6" />
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
          </svg>
          {deleteMutation.isPending ? t("deleting") : t("delete")}
        </button>
      </div>

      {showConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/60 p-4">
          <div
            className="w-full max-w-sm rounded-lg border p-6 shadow-xl"
            style={{
              background: design.colors.bg,
              borderColor: `${design.colors.primary}33`,
            }}
          >
            <h3
              className="mb-2 font-semibold text-lg"
              style={{ color: design.colors.text }}
            >
              {t("deleteConfirmTitle")}
            </h3>
            <p
              className="mb-6 text-sm"
              style={{ color: design.colors.text_dim }}
            >
              {t("deleteConfirm")}
            </p>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowConfirm(false)}
                className="rounded-md px-4 py-2 text-sm font-medium transition-opacity hover:opacity-80"
                style={{
                  color: design.colors.text_dim,
                  border: `1px solid ${design.colors.border}`,
                }}
              >
                {t("cancel")}
              </button>
              <button
                type="button"
                onClick={handleDelete}
                disabled={deleteMutation.isPending}
                className="rounded-md px-4 py-2 text-sm font-medium transition-opacity hover:opacity-80 disabled:opacity-50"
                style={{
                  background: "var(--color-destructive)",
                  color: "var(--color-destructive-foreground)",
                }}
              >
                {deleteMutation.isPending ? t("deleting") : t("delete")}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
