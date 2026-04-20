import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { Container } from "@/components/layout";
import { fetchCompletedProjects } from "@/lib/server-fetch";
import { FALLBACK_DESIGN_TOKENS } from "@/constants/blog";
import type { CarouselProjectListResponse } from "@/schemas/carousel";

interface PostCardProps {
  id: string;
  title: string;
  topic: string;
  niche: string;
  status: string;
  primaryColor: string;
  createdAt: string;
  readMoreText: string;
  descriptionText: string;
}

function PostCard({ id, title, topic, niche, status, primaryColor, createdAt, readMoreText, descriptionText }: PostCardProps) {
  const displayTitle = title || topic;

  return (
    <Link
      href={`/blog/${id}`}
      className="group block overflow-hidden rounded-xl border border-[var(--color-border)] bg-[var(--color-card)] p-6 transition-all hover:border-[var(--color-primary)]/50 hover:shadow-md"
    >
      <div className="mb-3 flex items-center gap-3">
        <span
          className="rounded px-2 py-0.5 font-mono text-xs font-bold uppercase tracking-wider"
          style={{
            color: primaryColor,
            background: `${primaryColor}14`,
          }}
        >
          {niche}
        </span>
        <span className="rounded bg-green-500/10 px-2 py-0.5 text-xs font-medium text-green-500">
          {status}
        </span>
      </div>
      <h2 className="mb-2 text-lg font-bold leading-snug transition-colors group-hover:text-[var(--color-primary)]">
        {displayTitle}
      </h2>
      <p className="mb-4 text-sm leading-relaxed text-[var(--color-muted-foreground)]">
        {descriptionText}
      </p>
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-[var(--color-primary)]">
          {readMoreText}
        </span>
        <span className="text-xs text-[var(--color-muted-foreground)]">
          {new Date(createdAt).toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
            year: "numeric",
          })}
        </span>
      </div>
    </Link>
  );
}

export default async function BlogPage() {
  const t = await getTranslations("blog");
  const data: CarouselProjectListResponse = await fetchCompletedProjects(20);
  const fallback = FALLBACK_DESIGN_TOKENS;

  return (
    <Container className="py-12">
      <Link
        href="/"
        className="mb-8 inline-flex items-center gap-2 text-sm text-[var(--color-muted-foreground)] transition-colors hover:text-[var(--color-primary)]"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="m12 19-7-7 7-7" />
          <path d="M19 12H5" />
        </svg>
        {t("backHome")}
      </Link>
      <h1 className="mb-2 text-3xl font-extrabold tracking-tight md:text-4xl">
        {t("title")}
      </h1>
      <p className="mb-10 text-lg text-[var(--color-muted-foreground)]">
        {t("subtitle")}
      </p>
      {data.items.length === 0 ? (
        <div className="rounded-xl border border-dashed border-[var(--color-border)] p-12 text-center">
          <p className="text-lg font-medium text-[var(--color-muted-foreground)]">
            {t("noPosts")}
          </p>
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {data.items.map((post) => (
            <PostCard
              key={post.id}
              id={post.id}
              title={post.title ?? ""}
              topic={post.topic}
              niche={post.niche}
              status={post.status}
              primaryColor={fallback.colors.primary}
              createdAt={post.created_at}
              readMoreText={t("readMore")}
              descriptionText={t("subtitle")}
            />
          ))}
        </div>
      )}
    </Container>
  );
}