"use client";

import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { Header } from "@/components/layout";
import { TopicForm } from "@/features/create/components";
import { useCreateCarousel } from "@/features/create/hooks";
import type { CarouselCreateRequest } from "@/schemas/carousel";
import { ROUTE_PATHS } from "@/constants/api";

export default function CreatePage() {
  const t = useTranslations("create");
  const router = useRouter();
  const createCarousel = useCreateCarousel();

  const handleSubmit = async (data: CarouselCreateRequest) => {
    const project = await createCarousel.mutateAsync(data);
    router.push(ROUTE_PATHS.CREATE_WORKSPACE(project.id));
  };

  return (
    <div className="min-h-screen">
      <Header />
      <main className="mx-auto max-w-4xl px-4 py-12">
        <div className="mb-8 space-y-2">
          <h1 className="font-bold text-2xl">{t("pageTitle")}</h1>
          <p className="text-[var(--color-text-muted)]">{t("pageDescription")}</p>
        </div>
        <TopicForm onSubmit={handleSubmit} isPending={createCarousel.isPending} />
      </main>
    </div>
  );
}
