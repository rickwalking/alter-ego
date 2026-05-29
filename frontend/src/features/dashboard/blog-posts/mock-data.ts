import type { DashboardBlogPost } from "./types";

export const MOCK_BLOG_POSTS: DashboardBlogPost[] = [
  {
    id: "1",
    title: "3800 repositorios internos do GitHub expostos",
    excerpt:
      "Deep analysis of the massive GitHub internal repository leak and what it means for software development security practices in 2026.",
    date: "May 26, 2026",
    views: 2400,
    comments: 48,
    category: "Security",
    featured: true,
  },
  {
    id: "2",
    title: "Claude Sonnet 4 vs GPT-5: Comparing the latest LLMs",
    excerpt:
      "Benchmark comparison of coding, reasoning, and agentic capabilities between the two leading models.",
    date: "May 24, 2026",
    views: 1800,
    comments: 32,
    category: "AI",
    featured: false,
  },
  {
    id: "3",
    title: "Building RAG Pipelines with LangGraph and Deep Agents",
    excerpt:
      "How to orchestrate complex multi-agent workflows using LangGraph's state machine and subagent patterns.",
    date: "May 20, 2026",
    views: 3100,
    comments: 56,
    category: "Architecture",
    featured: false,
  },
  {
    id: "4",
    title: "Event-Driven Workflows: Why We Chose Redis Streams",
    excerpt:
      "A technical deep dive into our event-driven architecture and the tradeoffs that led us to Redis Streams.",
    date: "May 15, 2026",
    views: 1200,
    comments: 18,
    category: "Dev",
    featured: false,
  },
  {
    id: "5",
    title: "Zero-Day Supply Chain Attacks in Open Source",
    excerpt:
      "Understanding the attack surface of modern open source dependencies and mitigation strategies.",
    date: "May 10, 2026",
    views: 890,
    comments: 12,
    category: "Security",
    featured: false,
  },
  {
    id: "6",
    title: "DeepSeek V4: The Open-Source AI Race Just Changed",
    excerpt:
      "Full analysis of DeepSeek V4's architecture, pricing, and competitive positioning against closed models.",
    date: "May 8, 2026",
    views: 4200,
    comments: 89,
    category: "AI",
    featured: false,
  },
];
