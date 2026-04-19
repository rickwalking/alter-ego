import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { Container } from "@/components/layout";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { MessageSquare, Database, Sparkles } from "lucide-react";

export default async function HomePage() {
  const t = await getTranslations("home");
  const tc = await getTranslations("common");

  return (
    <div className="flex-1">
      <section className="py-20 md:py-32">
        <Container>
          <div className="flex flex-col items-center text-center space-y-8">
            <div className="space-y-4 max-w-3xl">
              <h1 className="text-4xl md:text-6xl font-bold tracking-tight">
                {t("title")}{" "}
                <span className="text-[var(--color-primary)]">
                  {t("highlight")}
                </span>
              </h1>
              <p className="text-xl text-[var(--color-muted-foreground)] max-w-2xl mx-auto">
                {t("description")}
              </p>
            </div>
            <div className="flex flex-col sm:flex-row gap-4">
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

      <section className="py-20 bg-[var(--color-muted)]">
        <Container>
          <div className="grid md:grid-cols-3 gap-6">
            <Card>
              <CardHeader>
                <MessageSquare className="h-10 w-10 text-[var(--color-primary)] mb-2" aria-hidden="true" />
                <CardTitle>{t("features.intelligentChat.title")}</CardTitle>
                <CardDescription>
                  {t("features.intelligentChat.description")}
                </CardDescription>
              </CardHeader>
            </Card>

            <Card>
              <CardHeader>
                <Database className="h-10 w-10 text-[var(--color-primary)] mb-2" aria-hidden="true" />
                <CardTitle>{t("features.knowledgeManagement.title")}</CardTitle>
                <CardDescription>
                  {t("features.knowledgeManagement.description")}
                </CardDescription>
              </CardHeader>
            </Card>

            <Card>
              <CardHeader>
                <Sparkles className="h-10 w-10 text-[var(--color-primary)] mb-2" aria-hidden="true" />
                <CardTitle>{t("features.aiInsights.title")}</CardTitle>
                <CardDescription>
                  {t("features.aiInsights.description")}
                </CardDescription>
              </CardHeader>
            </Card>
          </div>
        </Container>
      </section>
    </div>
  );
}
