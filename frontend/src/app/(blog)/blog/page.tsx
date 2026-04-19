import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { Container } from "@/components/layout";
import { ArrowLeft } from "lucide-react";

const POSTS = [
  {
    slug: "gemma-4-google-compact-model",
    title: "Gemma 4: O Modelo Compacto da Google que Supera Modelos 20x Maiores",
    excerpt:
      "A Google lancou uma familia de modelos que desafiam a logica de escala. O Gemma 4 27B supera modelos com trilhoes de parametros nos benchmarks mais importantes.",
    date: "2025-04-01",
    badge: "AI/ML",
    readTime: "8 min",
    primaryColor: "#3b82f6",
    accentColor: "#f59e0b",
  },
];

export default async function BlogPage() {
  const t = await getTranslations("blog");

  return (
    <Container className="py-12">
      <Link
        href="/"
        className="mb-8 inline-flex items-center gap-2 text-sm text-[var(--color-muted-foreground)] transition-colors hover:text-[var(--color-primary)]"
      >
        <ArrowLeft className="h-4 w-4" />
        {t("backHome")}
      </Link>

      <h1 className="mb-2 text-3xl font-extrabold tracking-tight md:text-4xl">
        {t("title")}
      </h1>
      <p className="mb-10 text-lg text-[var(--color-muted-foreground)]">
        {t("subtitle")}
      </p>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {POSTS.map((post) => (
          <Link
            key={post.slug}
            href={`/blog/${post.slug}`}
            className="group block overflow-hidden rounded-xl border border-[var(--color-border)] bg-[var(--color-card)] p-6 transition-all hover:border-[var(--color-primary)]/50 hover:shadow-md"
          >
            <div className="mb-3 flex items-center gap-3">
              <span
                className="rounded px-2 py-0.5 font-mono text-xs font-bold uppercase tracking-wider"
                style={{
                  color: post.primaryColor,
                  background: `${post.primaryColor}14`,
                }}
              >
                {post.badge}
              </span>
              <span className="text-xs text-white/45">{post.readTime}</span>
            </div>

            <h2 className="mb-2 text-lg font-bold leading-snug transition-colors group-hover:text-[var(--color-primary)]">
              {post.title}
            </h2>

            <p className="mb-4 text-sm leading-relaxed text-[var(--color-muted-foreground)]">
              {post.excerpt}
            </p>

            <span className="text-sm font-medium text-[var(--color-primary)]">
              {t("readMore")}
            </span>
          </Link>
        ))}
      </div>
    </Container>
  );
}
