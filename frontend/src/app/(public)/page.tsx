import Link from "next/link";
import Image from "next/image";
import { getTranslations } from "next-intl/server";
import { Container } from "@/components/layout";
import { Button } from "@/components/ui/button";
import { MessageSquare, Database, Sparkles, ArrowRight } from "lucide-react";

const LATEST_POSTS = [
  {
    slug: "gemma-4-google-compact-model",
    title: "Gemma 4: O Modelo Compacto da Google que Supera Modelos 20x Maiores",
    excerpt:
      "A Google lancou uma familia de modelos que desafiam a logica de escala. O Gemma 4 27B supera modelos com trilhoes de parametros nos benchmarks mais importantes.",
    date: "2025-04-01",
    badge: "AI/ML",
    image: "/hero-ai-assistant.jpg",
    primaryColor: "#3b82f6",
    accentColor: "#f59e0b",
  },
];

export default async function HomePage() {
  const t = await getTranslations("home");
  const tc = await getTranslations("common");

  return (
    <div className="flex-1">
      {/* Hero Section */}
      <section className="relative overflow-hidden py-20 md:py-32">
        <Container>
          <div className="mx-auto max-w-5xl text-center">
            {/* Badge */}
            <div className="mb-6 inline-flex items-center gap-2 rounded-md border border-[var(--color-primary)]/30 bg-[var(--color-primary)]/10 px-4 py-2 font-mono text-xs font-bold uppercase tracking-widest text-[var(--color-primary)]">
              <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--color-primary)]" />
              {t("hero.badge")}
            </div>

            {/* Hero Image */}
            <div className="relative mx-auto mb-8 h-64 w-full max-w-3xl overflow-hidden rounded-2xl border border-[var(--color-border)] shadow-lg md:h-80">
              <Image
                src="/hero-ai-assistant-v2.jpg"
                alt="AI Assistant"
                fill
                className="object-cover"
                priority
              />
              <div className="absolute inset-0 bg-gradient-to-t from-[var(--color-background)] via-transparent to-transparent" />
            </div>

            {/* Title */}
            <h1 className="mb-4 text-4xl font-extrabold leading-tight tracking-tight md:text-6xl lg:text-7xl">
              {t("hero.title")}{" "}
              <span className="text-[var(--color-primary)]">
                {t("hero.highlight")}
              </span>
            </h1>

            {/* Subtitle */}
            <p className="mx-auto mb-10 max-w-2xl text-lg text-[var(--color-muted-foreground)] md:text-xl">
              {t("hero.subtitle")}
            </p>

            {/* CTAs */}
            <div className="flex flex-col items-center justify-center gap-4 sm:flex-row">
              <Link href="/chat">
                <Button size="lg" className="gap-2">
                  <MessageSquare className="h-5 w-5" aria-hidden="true" />
                  {tc("startChatting")}
                </Button>
              </Link>
              <Link href="/knowledge">
                <Button variant="outline" size="lg" className="gap-2">
                  <Database className="h-5 w-5" aria-hidden="true" />
                  {tc("manageKnowledge")}
                </Button>
              </Link>
            </div>
          </div>
        </Container>
      </section>

      {/* Latest Posts */}
      <section className="py-16 bg-[var(--color-muted)]/50">
        <Container>
          <div className="mb-10 flex items-end justify-between">
            <div>
              <h2 className="text-2xl font-bold md:text-3xl">
                {t("posts.title")}
              </h2>
              <p className="mt-2 text-[var(--color-muted-foreground)]">
                {t("posts.subtitle")}
              </p>
            </div>
            <Link
              href="/blog"
              className="hidden items-center gap-1 text-sm font-medium text-[var(--color-primary)] transition-colors hover:text-[var(--color-primary)]/80 md:flex"
            >
              {t("posts.viewAll")}
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>

          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {LATEST_POSTS.map((post) => (
              <Link
                key={post.slug}
                href={`/blog/${post.slug}`}
                className="group block overflow-hidden rounded-xl border border-[var(--color-border)] bg-[var(--color-card)] transition-all hover:border-[var(--color-primary)]/50 hover:shadow-md"
              >
                {/* Post Image */}
                <div className="relative h-48 w-full overflow-hidden">
                  <Image
                    src={post.image}
                    alt={post.title}
                    fill
                    className="object-cover transition-transform duration-300 group-hover:scale-105"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-[var(--color-card)] to-transparent" />
                </div>

                {/* Post Content */}
                <div className="p-5">
                  {/* Badge + Date */}
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
                    <span className="text-xs text-[var(--color-muted-foreground)]">
                      {new Date(post.date).toLocaleDateString("en-US", {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                      })}
                    </span>
                  </div>

                  {/* Title */}
                  <h3 className="mb-2 text-lg font-bold leading-snug transition-colors group-hover:text-[var(--color-primary)]">
                    {post.title}
                  </h3>

                  {/* Excerpt */}
                  <p className="text-sm leading-relaxed text-[var(--color-muted-foreground)]">
                    {post.excerpt}
                  </p>
                </div>
              </Link>
            ))}
          </div>
        </Container>
      </section>

      {/* Features */}
      <section className="py-20">
        <Container>
          <div className="mb-12 text-center">
            <h2 className="text-2xl font-bold md:text-3xl">
              {t("features.title")}
            </h2>
          </div>

          <div className="grid gap-6 md:grid-cols-3">
            {/* Feature 1 */}
            <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-card)] p-6 transition-all hover:border-[var(--color-primary)]/50 hover:shadow-md">
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-[var(--color-primary)]/10 text-[var(--color-primary)]">
                <MessageSquare className="h-6 w-6" aria-hidden="true" />
              </div>
              <h3 className="mb-2 text-lg font-bold">
                {t("features.intelligentChat.title")}
              </h3>
              <p className="text-sm leading-relaxed text-[var(--color-muted-foreground)]">
                {t("features.intelligentChat.description")}
              </p>
            </div>

            {/* Feature 2 */}
            <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-card)] p-6 transition-all hover:border-[var(--color-primary)]/50 hover:shadow-md">
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-[var(--color-primary)]/10 text-[var(--color-primary)]">
                <Database className="h-6 w-6" aria-hidden="true" />
              </div>
              <h3 className="mb-2 text-lg font-bold">
                {t("features.knowledgeManagement.title")}
              </h3>
              <p className="text-sm leading-relaxed text-[var(--color-muted-foreground)]">
                {t("features.knowledgeManagement.description")}
              </p>
            </div>

            {/* Feature 3 */}
            <div className="rounded-xl border border-[var(--color-border)] bg-[var(--color-card)] p-6 transition-all hover:border-[var(--color-primary)]/50 hover:shadow-md">
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-lg bg-[var(--color-primary)]/10 text-[var(--color-primary)]">
                <Sparkles className="h-6 w-6" aria-hidden="true" />
              </div>
              <h3 className="mb-2 text-lg font-bold">
                {t("features.aiInsights.title")}
              </h3>
              <p className="text-sm leading-relaxed text-[var(--color-muted-foreground)]">
                {t("features.aiInsights.description")}
              </p>
            </div>
          </div>
        </Container>
      </section>
    </div>
  );
}
