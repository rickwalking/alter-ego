/** How many curated suggestions one catalogue round shows. */
export const COVER_IDEA_CATALOGUE_SIZE = 6;

/** The visual dimensions every curated suggestion varies on, in prompt order. */
export const COVER_IDEA_DIMENSIONS = [
  "shot",
  "pose",
  "wardrobe",
  "location",
  "light",
] as const;

/** Options in each dimension pool (`create.coverIdeas.pools.<dimension>.<n>`). */
export const COVER_IDEA_POOL_SIZE = 8;

/** Props in each theme pool (`create.coverIdeas.props.<theme>.<n>`). */
export const COVER_IDEA_PROP_POOL_SIZE = 12;

/**
 * Topic words (lowercase, without accents) that pick a theme's prop pool; the
 * first theme with a matching word wins, else {@link COVER_IDEA_DEFAULT_THEME}.
 */
export const COVER_IDEA_THEME_KEYWORDS = {
  ai: [
    "ia",
    "ai",
    "agente",
    "agentes",
    "agent",
    "agents",
    "llm",
    "gpt",
    "chatgpt",
    "inteligencia",
    "intelligence",
    "robo",
    "robot",
    "automacao",
    "automation",
    "modelo",
    "model",
  ],
  code: [
    "codigo",
    "code",
    "software",
    "programacao",
    "programming",
    "dev",
    "developer",
    "desenvolvedor",
    "api",
    "cloud",
    "dados",
    "data",
  ],
  money: [
    "dinheiro",
    "money",
    "financas",
    "finance",
    "investimento",
    "investing",
    "investment",
    "mercado",
    "market",
    "economia",
    "economy",
    "preco",
    "price",
    "venda",
    "vendas",
    "sales",
  ],
  social: [
    "marketing",
    "instagram",
    "linkedin",
    "conteudo",
    "content",
    "rede",
    "redes",
    "social",
    "audiencia",
    "audience",
    "marca",
    "brand",
  ],
  career: [
    "carreira",
    "career",
    "emprego",
    "job",
    "trabalho",
    "work",
    "lideranca",
    "leadership",
    "time",
    "team",
    "gestao",
    "management",
    "produtividade",
    "productivity",
  ],
} as const;

export type CoverIdeaTheme = keyof typeof COVER_IDEA_THEME_KEYWORDS | "general";

/** The prop pool used when no theme keyword matches the topic. */
export const COVER_IDEA_DEFAULT_THEME: CoverIdeaTheme = "general";

/** Longest prompt the field keeps (the backend caps one AI idea at 400 too). */
export const COVER_PROMPT_MAX_LENGTH = 400;

/** Shortest topic the "Mais ideias" endpoint accepts (mirrors the backend). */
export const COVER_IDEA_TOPIC_MIN = 3;

/** Longest topic the "Mais ideias" endpoint accepts (mirrors the backend). */
export const COVER_IDEA_TOPIC_API_MAX = 500;

/** Fewest AI ideas one "Mais ideias" answer carries (mirrors the backend). */
export const COVER_IDEA_COUNT_MIN = 3;

/** Most AI ideas one "Mais ideias" answer carries (mirrors the backend). */
export const COVER_IDEA_COUNT_MAX = 6;

/** How long the "Copiado" confirmation stays after a copy, in milliseconds. */
export const COVER_PROMPT_COPIED_MS = 2000;

/** The dashboard locales the ideas endpoint writes in. */
export const COVER_IDEA_LOCALES = ["pt", "en"] as const;

/** Where the ideas on screen came from. */
export const COVER_IDEA_SOURCES = {
  CATALOGUE: "catalogue",
  AI: "ai",
} as const;

export type CoverIdeaSource =
  (typeof COVER_IDEA_SOURCES)[keyof typeof COVER_IDEA_SOURCES];
