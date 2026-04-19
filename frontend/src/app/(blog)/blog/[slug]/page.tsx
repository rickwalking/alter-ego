import Link from "next/link";
import Image from "next/image";
import { notFound } from "next/navigation";
import { Container } from "@/components/layout";
import { ArrowLeft, Calendar, Clock } from "lucide-react";

interface PostTheme {
  primary: string;
  accent: string;
  bg: string;
  bgLighter: string;
  text: string;
  text60: string;
  text48: string;
  text45: string;
  text06: string;
  insightText: string;
  fontFamily: string;
  monoFont: string;
}

interface PostData {
  slug: string;
  title: string;
  subtitle: string;
  date: string;
  readTime: string;
  badge: string;
  theme: PostTheme;
  images: string[];
  content: Array<
    | { type: "heading"; level: 2; text: string }
    | { type: "paragraph"; text: string }
    | { type: "list"; items: { term: string; definition: string }[] }
    | { type: "image"; src: string; alt: string }
    | { type: "stat-grid"; items: { value: string; label: string }[] }
    | { type: "insight"; text: string; author: string }
  >;
}

const POSTS: Record<string, PostData> = {
  "gemma-4-google-compact-model": {
    slug: "gemma-4-google-compact-model",
    title: "Gemma 4",
    subtitle: "O Modelo Compacto da Google que Supera Modelos 20x Maiores",
    date: "2025-04-01",
    readTime: "8 min",
    badge: "AI/ML",
    theme: {
      primary: "#3b82f6",
      accent: "#f59e0b",
      bg: "#0a0e17",
      bgLighter: "#0f1420",
      text: "#ffffff",
      text60: "rgba(255,255,255,0.63)",
      text48: "rgba(255,255,255,0.48)",
      text45: "rgba(255,255,255,0.45)",
      text06: "rgba(255,255,255,0.06)",
      insightText: "rgba(255,255,255,0.58)",
      fontFamily: "'Segoe UI', 'Helvetica Neue', Arial, sans-serif",
      monoFont: "'Courier New', monospace",
    },
    images: [
      "/gemma4-hero-1.jpg",
      "/gemma4-hero-2.jpg",
      "/gemma4-hero-3.jpg",
      "/gemma4-hero-4.jpg",
    ],
    content: [
      {
        type: "paragraph",
        text: "A Google lancou oficialmente a familia Gemma 4, e os numeros sao impressionantes. O modelo de 27B parametros supera o Llama 3.1 405B em benchmarks de raciocinio, e custa uma fracao para rodar.",
      },
      { type: "heading", level: 2, text: "A Familia Completa" },
      {
        type: "paragraph",
        text: "A Google nao lancou apenas um modelo. Sao quatro tamanhos, cada um otimizado para um cenario diferente:",
      },
      {
        type: "list",
        items: [
          {
            term: "Gemma 4 270M",
            definition:
              "Roda no celular, ideal para edge computing e dispositivos IoT",
          },
          {
            term: "Gemma 4 1B",
            definition: "Perfeito para laptops e prototipagem rapida",
          },
          {
            term: "Gemma 4 12B",
            definition:
              "O sweet spot para producao, bom equilibrio entre custo e performance",
          },
          {
            term: "Gemma 4 27B",
            definition:
              "O gigante compacto, supera modelos com trilhoes de parametros",
          },
        ],
      },
      { type: "image", src: "/gemma4-hero-2.jpg", alt: "Gemma 4 model family illustration" },
      { type: "heading", level: 2, text: "Benchmarks que Importam" },
      {
        type: "paragraph",
        text: "Os numeros falam por si. O Gemma 4 27B supera modelos significativamente maiores em tres areas criticas:",
      },
      {
        type: "stat-grid",
        items: [
          { value: "78.2", label: "MMLU-Pro" },
          { value: "89.4%", label: "HumanEval" },
          { value: "62.1", label: "GPQA Diamond" },
        ],
      },
      { type: "image", src: "/gemma4-hero-3.jpg", alt: "Gemma 4 benchmark comparison" },
      {
        type: "insight",
        text: "Um modelo de 27B que roda em uma unica GPU pode substituir chamadas de API caras para modelos proprietarios.",
        author: "Analise tecnica",
      },
      { type: "heading", level: 2, text: "Agentic e Multimodal" },
      {
        type: "paragraph",
        text: "O Gemma 4 nao e apenas um modelo de texto. Suporta nativamente:",
      },
      {
        type: "list",
        items: [
          {
            term: "Function calling",
            definition: "com estruturacao automatica de saidas",
          },
          {
            term: "Visao computacional",
            definition: "para analise de imagens e documentos",
          },
          {
            term: "Audio processing",
            definition: "para transcricao e compreensao",
          },
          {
            term: "Orquestracao de agentes",
            definition: "com planejamento multi-etapa",
          },
        ],
      },
      { type: "image", src: "/gemma4-hero-4.jpg", alt: "Gemma 4 multimodal capabilities" },
      { type: "heading", level: 2, text: "O que Isso Significa para Devs" },
      {
        type: "paragraph",
        text: "Se voce esta construindo aplicacoes com LLMs, o Gemma 4 muda a equacao de custo-beneficio. Um modelo de 27B que roda em uma unica GPU pode substituir chamadas de API caras para modelos proprietarios.",
      },
      {
        type: "paragraph",
        text: "A combinacao de agentic capabilities com multimodalidade nativa significa que voce pode construir pipelines complexos com um unico modelo, simplificando sua arquitetura.",
      },
    ],
  },
};

export function generateStaticParams() {
  return Object.keys(POSTS).map((slug) => ({ slug }));
}

export default async function BlogPostPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const post = POSTS[slug];

  if (!post) {
    notFound();
  }

  const t = post.theme;

  return (
    <div
      className="dark min-h-screen"
      style={{
        background: t.bg,
        fontFamily: t.fontFamily,
      }}
    >
      {/* Background glows */}
      <div className="pointer-events-none fixed inset-0">
        <div
          className="absolute -top-24 right-0 h-96 w-96 rounded-full"
          style={{
            background: `radial-gradient(circle, ${t.primary}0D 0%, transparent 70%)`,
          }}
        />
        <div
          className="absolute -bottom-24 left-0 h-80 w-80 rounded-full"
          style={{
            background: `radial-gradient(circle, ${t.accent}0D 0%, transparent 70%)`,
          }}
        />
      </div>

      <Container className="relative z-10 py-12">
        <Link
          href="/blog"
          className="mb-8 inline-flex items-center gap-2 text-sm transition-colors hover:opacity-80"
          style={{ color: t.text45 }}
        >
          <ArrowLeft className="h-4 w-4" />
          Back to posts
        </Link>

        <article className="mx-auto max-w-3xl">
          {/* Badge */}
          <div
            className="mb-6 inline-flex items-center gap-2 rounded-md border px-4 py-2 font-mono text-xs font-bold uppercase tracking-widest"
            style={{
              borderColor: `${t.primary}4D`,
              background: `${t.primary}14`,
              color: t.primary,
              fontFamily: t.monoFont,
            }}
          >
            {post.badge}
          </div>

          {/* Title */}
          <h1
            className="mb-3 text-5xl font-extrabold leading-tight md:text-6xl"
            style={{ color: t.text }}
          >
            {post.title}
          </h1>

          {/* Subtitle */}
          <p
            className="mb-6 text-2xl leading-relaxed"
            style={{ color: t.text48 }}
          >
            {post.subtitle}
          </p>

          {/* Meta */}
          <div className="mb-8 flex items-center gap-4 border-b pb-6" style={{ borderColor: t.text06 }}>
            <span className="flex items-center gap-1 text-sm" style={{ color: t.text45 }}>
              <Calendar className="h-4 w-4" />
              {new Date(post.date).toLocaleDateString("en-US", {
                month: "long",
                day: "numeric",
                year: "numeric",
              })}
            </span>
            <span className="flex items-center gap-1 text-sm" style={{ color: t.text45 }}>
              <Clock className="h-4 w-4" />
              {post.readTime}
            </span>
          </div>

          {/* Hero Image */}
          <div
            className="relative mb-10 h-72 w-full overflow-hidden rounded-2xl md:h-96"
            style={{
              border: `1px solid ${t.primary}33`,
              boxShadow: `0 0 60px ${t.primary}1F, 0 20px 40px rgba(0,0,0,0.4)`,
            }}
          >
            <Image
              src={post.images[0]}
              alt={post.title}
              fill
              className="object-cover"
              priority
            />
            <div
              className="absolute inset-0"
              style={{
                background: `linear-gradient(to bottom, transparent 40%, ${t.bg} 100%)`,
              }}
            />
          </div>

          {/* Content */}
          <div className="space-y-6">
            {post.content.map((block, i) => {
              if (block.type === "heading") {
                return (
                  <h2
                    key={i}
                    className="mt-10 mb-6 text-3xl font-extrabold leading-tight"
                    style={{ color: t.text }}
                  >
                    {block.text}
                  </h2>
                );
              }

              if (block.type === "image") {
                return (
                  <div
                    key={i}
                    className="relative h-56 w-full overflow-hidden rounded-xl md:h-72"
                    style={{
                      border: `1px solid ${t.primary}33`,
                      boxShadow: `0 0 40px ${t.primary}1A, 0 12px 30px rgba(0,0,0,0.3)`,
                    }}
                  >
                    <Image
                      src={block.src}
                      alt={block.alt}
                      fill
                      className="object-cover"
                    />
                  </div>
                );
              }

              if (block.type === "stat-grid") {
                return (
                  <div
                    key={i}
                    className="grid grid-cols-3 gap-4 rounded-xl p-5"
                    style={{ background: t.bgLighter }}
                  >
                    {block.items.map((item, j) => (
                      <div key={j} className="text-center">
                        <div
                          className="mb-1 text-4xl font-black"
                          style={{ color: t.primary }}
                        >
                          {item.value}
                        </div>
                        <div className="text-sm" style={{ color: t.text45 }}>
                          {item.label}
                        </div>
                      </div>
                    ))}
                  </div>
                );
              }

              if (block.type === "insight") {
                return (
                  <div
                    key={i}
                    className="rounded-l-lg border-l-4 p-5"
                    style={{
                      borderColor: t.accent,
                      background: `${t.accent}08`,
                    }}
                  >
                    <p
                      className="mb-2 text-lg italic leading-relaxed"
                      style={{ color: t.insightText }}
                    >
                      "{block.text}"
                    </p>
                    <p className="text-sm" style={{ color: t.text45 }}>
                      — {block.author}
                    </p>
                  </div>
                );
              }

              if (block.type === "list") {
                return (
                  <ul key={i} className="space-y-3">
                    {block.items.map((item, j) => (
                      <li
                        key={j}
                        className="flex gap-3 text-base"
                        style={{ color: t.text60 }}
                      >
                        <span
                          className="shrink-0 text-lg"
                          style={{ color: t.primary }}
                        >
                          •
                        </span>
                        <span>
                          <strong style={{ color: t.text }}>
                            {item.term}
                          </strong>
                          {` — ${item.definition}`}
                        </span>
                      </li>
                    ))}
                  </ul>
                );
              }

              return (
                <p
                  key={i}
                  className="text-base leading-relaxed"
                  style={{ color: t.text60 }}
                >
                  {block.text}
                </p>
              );
            })}
          </div>
        </article>
      </Container>
    </div>
  );
}
